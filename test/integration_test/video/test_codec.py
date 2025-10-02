import av
from loguru import logger

from app.network.websocket import WebSocketClient
from app.video.codec import VideoCodec
from app.video.webcam import Webcam


def test_123() -> None:
    codecs = sorted(av.codecs_available)
    for codec in codecs:
        logger.debug(codec)


def test_encode() -> None:
    width = 1280
    height = 720
    fps = 20

    camera = Webcam(1, width=width, height=height, fps=fps)
    encoded_stream = VideoCodec.encode_h264(
        frames=camera.capture_frames(),
        width=width,
        height=height,
        fps=fps,
    )
    WebSocketClient.stub_sender(encoded_stream)
