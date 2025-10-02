from collections.abc import Generator

from loguru import logger


class WebSocket:
    @classmethod
    def stub_sender(cls, encoded_stream: Generator[bytes, None, None]) -> None:
        for packet in encoded_stream:
            logger.debug(f"[stub send] packet size: {len(packet)} bytes")
