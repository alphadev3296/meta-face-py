import asyncio
import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiohttp
import cv2
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from jose import jwt
from loguru import logger

from app.config.auth import config as cfg_auth
from app.video.videotrack import WebcamVideoTrack
from app.video.webcam import CvFrame, Webcam


class WebRTCClient:
    def __init__(
        self,
        offer_url: str,
        jwt_token: str,
        b64_photo: str,
        read_frame_func: Callable[[], tuple[bool, CvFrame]],
        on_recv_frame_callback: Callable[[CvFrame, int], None] | None = None,
    ) -> None:
        self.pc = RTCPeerConnection()
        self.recv_frames: asyncio.Queue[CvFrame] = asyncio.Queue(maxsize=10)

        self.offer_url = offer_url
        self.jwt_token = jwt_token
        self.b64_photo = b64_photo
        self.read_frame_func = read_frame_func
        self.on_recv_frame_callback = on_recv_frame_callback

    async def connect(self) -> None:
        """Establish WebRTC connection with server"""

        # Add webcam track
        webcam_track = WebcamVideoTrack(read_frame_func=self.read_frame_func)
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
                        img = frame.to_ndarray(format="rgb24")  # type: ignore  # noqa: PGH003
                        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

                        # Call external callback
                        if self.on_recv_frame_callback is not None:
                            self.on_recv_frame_callback(img, frame.pts or 0)

                        # Put frame in queue (non-blocking)
                        if self.recv_frames.full():
                            self.recv_frames.get_nowait()
                        self.recv_frames.put_nowait(img)
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
                self.offer_url,
                json={
                    "sdp": self.pc.localDescription.sdp,
                    "type": self.pc.localDescription.type,
                    "token": self.jwt_token,
                    "photo": self.b64_photo,
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
                frame = await asyncio.wait_for(self.recv_frames.get(), timeout=1.0)

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
    server_url = "http://localhost:8000"
    device_id = 1
    width = 640  # Video width in pixels
    height = 480  # Video height in pixels
    fps = 30  # Frames per second

    webcam = Webcam(
        device=device_id,
        width=width,
        height=height,
        fps=fps,
    )
    webcam.open()

    logger.info("Starting WebRTC client:")
    logger.info(f"  Resolution: {width}x{height}")
    logger.info(f"  FPS: {fps}")

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

        def recv_frame(frame: CvFrame, pts: int) -> None:
            logger.debug(f"Received frame {pts}: {frame.shape}")

        client = WebRTCClient(
            offer_url=f"{server_url}/offer",
            jwt_token=jwt_token,
            b64_photo=photo_data,
            read_frame_func=webcam.read,
            on_recv_frame_callback=recv_frame,
        )

        await client.connect()
        await client.display_loop()
    except KeyboardInterrupt:
        logger.debug("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
