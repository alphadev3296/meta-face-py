import time
from collections.abc import Generator
from typing import Any

import cv2
import numpy as np
from pygrabber.dshow_graph import FilterGraph

CvFrame = np.ndarray[Any, Any]


class Webcam:
    def __init__(self, device: int, width: int, height: int, fps: int) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.cap: cv2.VideoCapture | None = None

    @classmethod
    def list_webcams(cls) -> list[tuple[int, str]]:
        graph = FilterGraph()  # type: ignore  # noqa: PGH003
        device_names = graph.get_input_devices()  # type: ignore  # noqa: PGH003 # Human-readable device names

        available = []
        for i, name in enumerate(device_names):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Check if it opens
            if cap.isOpened():
                available.append((i, name))
            cap.release()
        return available

    def open(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        cap = cv2.VideoCapture(self.device, cv2.CAP_DSHOW)
        if not cap.isOpened():
            msg = f"Could not open camera {self.device}"
            raise RuntimeError(msg)

        self.cap = cap
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def close(self) -> None:
        if self.cap is None:
            return

        self.cap.release()
        self.cap = None

    def read(self) -> tuple[bool, CvFrame]:
        if self.cap is None:
            return False, CvFrame(0)
        return self.cap.read()

    def __del__(self) -> None:
        self.close()

    def capture_frames(self) -> Generator[CvFrame, None, None]:
        try:
            self.open()

            while True:
                ret, frame = self.read()
                if not ret:
                    break

                # Resize if needed
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))

                yield frame

                time.sleep(1 / self.fps)
        finally:
            self.close()
