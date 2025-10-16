from collections.abc import Callable
from typing import Any

import cv2
import numpy as np
from pygrabber.dshow_graph import FilterGraph

CvFrame = np.ndarray[Any, Any]


class Webcam:
    def __init__(
        self,
        device: int,
        width: int,
        height: int,
        fps: int,
        pre_process_callback: Callable[[CvFrame], CvFrame] | None = None,
    ) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps

        self.pre_process_callback = pre_process_callback

        self.cap: cv2.VideoCapture | None = None

    def __del__(self) -> None:
        self.close()

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
        self.close()

        cap = cv2.VideoCapture(self.device, cv2.CAP_DSHOW)
        if not cap.isOpened():
            msg = f"Could not open camera {self.device}"
            raise RuntimeError(msg)

        self.cap = cap
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def read(self) -> tuple[bool, CvFrame]:
        if self.cap is None:
            return False, CvFrame(0)

        ok, frame = self.cap.read()
        if not ok:
            return False, CvFrame(0)

        if self.pre_process_callback is not None:
            frame = self.pre_process_callback(frame)

        return True, frame
