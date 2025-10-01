import cv2
from pygrabber.dshow_graph import FilterGraph


class Webcam:
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
