import asyncio
import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiohttp
import cv2
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from jose import jwt
from loguru import logger

from app.config.auth import config as cfg_auth
from app.video.videotrack import WebcamVideoTrack


class WebRTCClient:
    def __init__(
        self,
        device_id: int,
        width: int,
        height: int,
        fps: int,
    ) -> None:
        self.pc = RTCPeerConnection()
        self.processed_frames = asyncio.Queue(maxsize=10)

        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps

    async def connect(
        self,
        offer_url: str,
        jwt_token: str,
        photo_data: str,
    ) -> None:
        """Establish WebRTC connection with server"""

        # Add webcam track
        webcam_track = WebcamVideoTrack(
            device_id=self.device_id,
            width=self.width,
            height=self.height,
            fps=self.fps,
        )
        self.pc.addTrack(webcam_track)

        # Handle incoming video track (processed frames from server)
        @self.pc.on("track")
        async def on_track(track: MediaStreamTrack) -> None:
            logger.debug(f"Receiving {track.kind} track")
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
                        logger.error(f"Error receiving frame: {e}")
                        break

        # Create offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        # Send offer to server
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                offer_url,
                json={
                    "sdp": self.pc.localDescription.sdp,
                    "type": self.pc.localDescription.type,
                    "token": jwt_token,
                    "photo": photo_data,
                },
                headers={"Content-Type": "application/json"},
            ) as response,
        ):
            answer = await response.json()

            # Set remote description
            await self.pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type=answer["type"]))

        logger.success("WebRTC connection established")

    async def display_loop(self) -> None:
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
                logger.error(f"Display error: {e}")
                break

        cv2.destroyAllWindows()

    async def close(self) -> None:
        """Close connection and cleanup"""
        await self.pc.close()
        logger.debug("Connection closed")


async def main() -> None:
    # Configuration
    cfg = {
        "server_url": "http://localhost:8000",
        "device_id": 1,
        "width": 640,  # Video width in pixels
        "height": 480,  # Video height in pixels
        "fps": 30,  # Frames per second
    }

    client = WebRTCClient(
        device_id=cfg["device_id"],
        width=cfg["width"],
        height=cfg["height"],
        fps=cfg["fps"],
    )

    logger.info("Starting WebRTC client:")
    logger.info(f"  Resolution: {cfg['width']}x{cfg['height']}")
    logger.info(f"  FPS: {cfg['fps']}")

    try:
        # Read photo image
        with Path(r"C:\Users\alpha\Downloads\output.png").open("rb") as f:  # noqa: ASYNC230
            photo_data = base64.b64encode(f.read()).decode("utf-8")

        jwt_token = jwt.encode(
            {
                "sub": "",
                "exp": datetime.now(tz=UTC) + timedelta(minutes=cfg_auth.JWT_TOKEN_EXPIRE_MINS),
                "tone_enhance": False,
                "face_enhance": False,
            },
            "qC7kQqEnscXo4A3Zh1p6uK2zBdRno8cYPm5t7UHs",
            algorithm=cfg_auth.JWT_ALGORITHM,
        )

        await client.connect(
            offer_url=f"{cfg['server_url']}/offer",
            jwt_token=jwt_token,
            photo_data=photo_data,
        )
        await client.display_loop()
    except KeyboardInterrupt:
        logger.debug("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
