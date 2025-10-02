import asyncio
import os
from collections.abc import Generator

from app.network.websocket import WebSocketClient


def test_byte_stream() -> None:
    def face_byte_stream() -> Generator[bytes, None, None]:
        for i in range(10):
            yield os.urandom(1024 + i)

    async def send_bytes() -> None:
        client = WebSocketClient("ws://localhost:8000/ws/video", reconnect_delay=3, max_retries=3)
        await client.send_stream(face_byte_stream())

    asyncio.run(send_bytes())
