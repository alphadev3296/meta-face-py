from collections.abc import Generator

import av
from loguru import logger

from app.network.websocket import WebSocketClient
from app.video.codec import VideoCodec
from app.video.webcam import CvFrame, Webcam


def test_123() -> None:
    codecs = sorted(av.codecs_available)
    for codec in codecs:
        logger.debug(codec)


def test_encode() -> None:
    width = 1280
    height = 720
    fps = 20

    camera = Webcam(1, width=width, height=height, fps=fps)
    camera.open()

    def frame_generator() -> Generator[CvFrame, None, None]:
        for i in range(30):
            logger.debug(f"Frame {i}")
            ret, frame = camera.read()
            if not ret:
                break
            yield frame

    encoded_stream = VideoCodec.encode_h264(
        frames=frame_generator(),
        width=width,
        height=height,
        fps=fps,
    )
    WebSocketClient.stub_sender(encoded_stream)
