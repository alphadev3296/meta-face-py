import cv2
from aiortc import VideoStreamTrack
from av import VideoFrame


class WebcamVideoTrack(VideoStreamTrack):
    """Video track that captures from webcam"""

    def __init__(
        self,
        device_id: int,
        width: int = 1280,
        height: int = 720,
        fps: int = 20,
    ) -> None:
        super().__init__()
        self.cap = cv2.VideoCapture(device_id, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        ret, frame = self.cap.read()
        if not ret:
            msg = "Failed to capture frame"
            raise RuntimeError(msg)

        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create VideoFrame
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    def stop(self) -> None:
        if self.cap:
            self.cap.release()
