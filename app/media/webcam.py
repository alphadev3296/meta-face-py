import threading
import time
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
        self.last_frame: CvFrame = np.zeros((self.height, self.width, 3), np.uint8)
        self.last_frame_lock = threading.Lock()

        self.read_thread: threading.Thread | None = None
        self.read_thread_stop_event = threading.Event()

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

        self.read_thread_stop_event.clear()
        self.read_thread = threading.Thread(target=self.read_loop, daemon=True)
        self.read_thread.start()

    def close(self) -> None:
        if self.read_thread is not None:
            if not self.read_thread_stop_event.is_set():
                self.read_thread_stop_event.set()
            self.read_thread.join()
            self.read_thread = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def _read(self) -> tuple[bool, CvFrame]:
        if self.cap is None:
            return False, CvFrame(0)

        ok, frame = self.cap.read()
        if not ok:
            return False, CvFrame(0)

        if self.pre_process_callback is not None:
            frame = self.pre_process_callback(frame)

        return True, frame

    def read_loop(self) -> None:
        last_tstamp = time.time()
        delay = 1.0 / self.fps
        while not self.read_thread_stop_event.is_set():
            if time.time() - last_tstamp >= delay:
                last_tstamp = time.time()

                ok, frame = self._read()
                if ok:
                    self.last_frame = frame
            time.sleep(0.001)

    def read(self) -> CvFrame:
        return self.last_frame.copy()
