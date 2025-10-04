import cv2
from loguru import logger

from app.video.webcam import Webcam


def test_list_devices() -> None:
    devices = Webcam.list_webcams()
    for i, name in devices:
        logger.debug(f"Device {i}: {name}")


def test_open_close() -> None:
    device = 0
    width = 640
    height = 480
    fps = 10

    webcam = Webcam(device, width, height, fps)
    webcam.open()
    cap = webcam.cap
    assert cap is not None

    assert cap.isOpened()
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    actual_fps = cap.get(cv2.CAP_PROP_FPS)

    webcam.close()

    logger.debug(f"expected: {width} x {height} x {fps}")
    logger.debug(f"actual: {actual_width} x {actual_height} x {actual_fps}")


def test_frame_view_raw() -> None:
    logger.debug("Press 'q' to quit")

    webcam = Webcam(1, 1280, 720, 30)
    webcam.open()

    while True:
        ret, frame = webcam.read()
        if not ret:
            break

        cv2.imshow("Camera Test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):  # Press 'q' to quit
            break

    webcam.close()
    cv2.destroyAllWindows()
