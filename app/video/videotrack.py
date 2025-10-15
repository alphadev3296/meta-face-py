from collections.abc import Callable

import cv2
from aiortc import VideoStreamTrack
from av import VideoFrame

from app.video.webcam import CvFrame


class WebcamVideoTrack(VideoStreamTrack):
    """Video track that captures from webcam"""

    def __init__(
        self,
        read_frame_func: Callable[[], tuple[bool, CvFrame]],
        on_camera_frame_callback: Callable[[CvFrame], None] | None = None,
    ) -> None:
        super().__init__()
        self.read_func = read_frame_func
        self.on_camera_frame_callback = on_camera_frame_callback

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        # Capture frame
        ret, frame = self.read_func()
        if not ret:
            msg = "Failed to capture frame"
            raise RuntimeError(msg)

        # Call external callback
        if self.on_camera_frame_callback is not None:
            self.on_camera_frame_callback(frame)

        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create VideoFrame
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")  # type: ignore  # noqa: PGH003
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame
