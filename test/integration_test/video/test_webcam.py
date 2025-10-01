from loguru import logger

from app.video.webcam import WebCam


def test_list_devices() -> None:
    devices = WebCam.list_webcams()
    for i, name in devices:
        logger.debug(f"Device {i}: {name}")
