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

        self.cap = cv2.VideoCapture(self.device, cv2.CAP_DSHOW)
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
