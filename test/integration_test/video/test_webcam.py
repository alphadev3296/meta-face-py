from loguru import logger

from app.video.webcam import Webcam


def test_list_devices() -> None:
    devices = Webcam.list_webcams()
    for i, name in devices:
        logger.debug(f"Device {i}: {name}")
