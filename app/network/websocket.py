import asyncio
from collections.abc import Callable, Generator

import websockets
from loguru import logger


class WebSocketClient:
    def __init__(self, uri: str, reconnect_delay: int = 5, max_retries: int = 5) -> None:
        """
        Args:
            uri (str): WebSocket server URI, e.g. "ws://localhost:8000/ws/video"
            reconnect_delay (int): Seconds to wait between reconnect attempts.
            max_retries (int): How many times to retry before giving up (-1 = infinite).
        """
        self.uri = uri
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries

    async def send_stream(
        self,
        byte_stream: Generator[bytes, None, None],
        callback_connected: Callable[[], None] | None = None,
        callback_disconnected: Callable[[], None] | None = None,
    ) -> None:
        """
        Connect to server and send H264 stream chunks.

        Args:
            byte_stream (Generator[bytes]): yields byte packets (H264 chunks).
        """
        attempt = 0
        while self.max_retries == -1 or attempt < self.max_retries:
            try:
                logger.info(f"Connecting to {self.uri} (attempt {attempt + 1})")
                async with websockets.connect(self.uri, max_size=None) as ws:
                    logger.info("WebSocket connection established.")
                    if callback_connected is not None:
                        callback_connected()

                    for packet in byte_stream:
                        await ws.send(packet)
                        logger.debug(f"Sent packet size: {len(packet)} bytes")

                    logger.info("Finished sending stream.")
                    if callback_disconnected is not None:
                        callback_disconnected()

                    return  # Done streaming if no errors
            except (OSError, websockets.exceptions.WebSocketException) as e:
                logger.error(f"WebSocket error: {e}. Retrying in {self.reconnect_delay}s...")
                attempt += 1
                await asyncio.sleep(self.reconnect_delay)

        logger.error("Max retries exceeded. Stream could not be sent.")
        if callback_disconnected is not None:
            callback_disconnected()

    @classmethod
    def stub_sender(cls, encoded_stream: Generator[bytes, None, None]) -> None:
        """Retain simple stub for offline testing."""
        for packet in encoded_stream:
            logger.debug(f"[stub send] packet size: {len(packet)} bytes")
