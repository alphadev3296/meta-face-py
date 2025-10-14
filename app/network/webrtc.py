import asyncio

import aiohttp
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription

from app.video.videotrack import WebcamVideoTrack


class WebRTCClient:
    def __init__(self, server_url, width=640, height=480, fps=30, bitrate=2000000):
        self.server_url = server_url
        self.pc = RTCPeerConnection()
        self.processed_frames = asyncio.Queue(maxsize=10)
        self.width = width
        self.height = height
        self.fps = fps
        self.bitrate = bitrate

    async def connect(self):
        """Establish WebRTC connection with server"""

        # Add webcam track
        webcam_track = WebcamVideoTrack(width=self.width, height=self.height, fps=self.fps)
        sender = self.pc.addTrack(webcam_track)

        # Handle incoming video track (processed frames from server)
        @self.pc.on("track")
        async def on_track(track):
            print(f"Receiving {track.kind} track")
            if track.kind == "video":
                while True:
                    try:
                        frame = await track.recv()
                        # Convert to numpy array for display
                        img = frame.to_ndarray(format="rgb24")
                        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

                        # Put frame in queue (non-blocking)
                        if self.processed_frames.full():
                            self.processed_frames.get_nowait()
                        self.processed_frames.put_nowait(img)
                    except Exception as e:
                        print(f"Error receiving frame: {e}")
                        break

        # Create offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        # Apply encoding parameters
        if sender:
            try:
                parameters = sender.getParameters()

                if not parameters.encodings:
                    parameters.encodings = [{}]

                # Set bitrate and framerate
                parameters.encodings[0].maxBitrate = self.bitrate

                if hasattr(parameters.encodings[0], "maxFramerate"):
                    parameters.encodings[0].maxFramerate = self.fps

                await sender.setParameters(parameters)

                print("Encoding parameters applied:")
                print(f"  Bitrate: {self.bitrate / 1000000:.1f} Mbps")
                print(f"  Framerate: {self.fps} fps")

            except Exception as e:
                print(f"Warning: Could not set encoding parameters: {e}")

        # Send offer to server
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self.server_url}/offer",
                json={"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type},
                headers={"Content-Type": "application/json"},
            ) as response,
        ):
            answer = await response.json()

            # Set remote description
            await self.pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type=answer["type"]))

        print("WebRTC connection established")

    async def display_loop(self):
        """Display processed frames"""
        cv2.namedWindow("Processed Stream", cv2.WINDOW_NORMAL)

        while True:
            try:
                # Get frame from queue with timeout
                frame = await asyncio.wait_for(self.processed_frames.get(), timeout=1.0)

                cv2.imshow("Processed Stream", frame)

                # Break on 'q' key
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            except TimeoutError:
                # No frame available, check for key press
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            except Exception as e:
                print(f"Display error: {e}")
                break

        cv2.destroyAllWindows()

    async def close(self):
        """Close connection and cleanup"""
        await self.pc.close()
        print("Connection closed")


async def main():
    # Configuration
    CONFIG = {
        "server_url": "http://localhost:8080",
        "width": 640,  # Video width in pixels
        "height": 480,  # Video height in pixels
        "fps": 30,  # Frames per second
        "bitrate": 2000000,  # Bitrate in bps (2000000 = 2 Mbps)
    }

    client = WebRTCClient(
        server_url=CONFIG["server_url"],
        width=CONFIG["width"],
        height=CONFIG["height"],
        fps=CONFIG["fps"],
        bitrate=CONFIG["bitrate"],
    )

    print(f"Starting WebRTC client:")
    print(f"  Resolution: {CONFIG['width']}x{CONFIG['height']}")
    print(f"  FPS: {CONFIG['fps']}")
    print(f"  Bitrate: {CONFIG['bitrate'] / 1000000:.1f} Mbps")

    try:
        await client.connect()
        await client.display_loop()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
