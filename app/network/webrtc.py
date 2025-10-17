import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import aiohttp
import cv2
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.codecs import h264, vpx
from loguru import logger

from app.media.videotrack import WebcamVideoTrack
from app.media.webcam import CvFrame

# Set codec parameters for good quality
h264.DEFAULT_BITRATE = 20 << 20  # 20 Mbps
h264.MAX_FRAME_RATE = 30
vpx.DEFAULT_BITRATE = 20 << 20  # 20 Mbps
vpx.MAX_FRAME_RATE = 30


class WebRTCClient:
    def __init__(
        self,
        offer_url: str,
        jwt_token: str,
        b64_photo: str,
        read_frame_func: Callable[[], CvFrame],
        on_recv_frame_callback: Callable[[CvFrame, int], Coroutine[Any, Any, None]] | None = None,
        on_disconnect_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self.pc = RTCPeerConnection()
        self.recv_frames: asyncio.Queue[CvFrame] = asyncio.Queue(maxsize=10)

        self.offer_url = offer_url
        self.jwt_token = jwt_token
        self.b64_photo = b64_photo
        self.read_frame_func = read_frame_func

        self.on_recv_frame_callback = on_recv_frame_callback
        self.on_disconnect_callback = on_disconnect_callback

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
                            await self.on_recv_frame_callback(img, frame.pts or 0)

                        # Put frame in queue (non-blocking)
                        if self.recv_frames.full():
                            self.recv_frames.get_nowait()
                        self.recv_frames.put_nowait(img)
                    except Exception as e:
                        logger.error(f"Error receiving frame: {e}")
                        if self.on_disconnect_callback is not None:
                            await self.on_disconnect_callback()
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

    async def get_remote_frame(self, timeout: float | None = None) -> CvFrame:  # noqa: ASYNC109
        """
        Get processed frame from server.

        Args:
            timeout (float | None, optional): Timeout in seconds. Defaults to None.
                If None, will block until a frame is available.

        Returns:
            CvFrame: Processed frame

        Raises:
            TimeoutError: If no frame is available within the specified timeout.
        """
        return (
            await asyncio.wait_for(self.recv_frames.get(), timeout=timeout)
            if timeout is not None
            else await self.recv_frames.get()
        )

    async def close(self) -> None:
        """Close connection and cleanup"""
        await self.pc.close()
        logger.debug("Connection closed")
