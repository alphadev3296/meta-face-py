import asyncio
import contextlib
from collections.abc import Callable, Generator

import websockets
from loguru import logger

from app.video.h264 import H264VideoProcessor
from app.video.webcam import CvFrame


class WebSocketVideoClient:
    def __init__(
        self,
        uri: str,
        reconnect_delay: int = 5,
        max_retries: int = 3,
    ) -> None:
        """
        Single-frame loop WebSocket client (send one, receive one).
        """
        self.uri = uri
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries
        self.processor = H264VideoProcessor()

    async def _send_task(
        self,
        ws: websockets.ClientConnection,
        frames: Generator["CvFrame", None, None],
        processor: H264VideoProcessor,
        interval: float = 0.01,
    ) -> None:
        packet_count = 0
        for frame in frames:
            # Initialize encoder if not done
            if not processor.encoder_initialized:
                processor.init_encoder(frame.shape[1], frame.shape[0])

            # Encode frame (may produce multiple packets)
            for packet in processor.encode_frame(frame):
                if packet:
                    await ws.send(packet)
                    packet_count += 1
                    logger.debug(f"Sent packet {packet_count} ({len(packet)} bytes)")

                    await asyncio.sleep(interval)
        logger.info(f"Send task finished. Sent packets={packet_count}")

    async def _recv_task(
        self,
        ws: websockets.ClientConnection,
        processor: H264VideoProcessor,
        frame_callback: Callable[["CvFrame", int], None],
        interval: float = 0.0001,
    ) -> None:
        frame_count = 0
        async for message in ws:
            if isinstance(message, bytes):
                decoded_frames = processor.decode_frame(message)
                for f in decoded_frames:
                    frame_callback(f, frame_count)
                    frame_count += 1

                    await asyncio.sleep(interval)
            else:
                logger.warning(f"Received non-binary message: {message}")
        logger.info(f"Recv task finished. Received frames={frame_count}")

    async def _run_async(
        self,
        frames: Generator["CvFrame", None, None],
        frame_callback: Callable[["CvFrame", int], None],
    ) -> None:
        attempt = 0
        while self.max_retries == -1 or attempt < self.max_retries:
            try:
                async with websockets.connect(self.uri, max_size=None) as ws:
                    logger.info(f"Connected to WebSocket: {self.uri}")

                    # Reset codec state
                    self.processor.cleanup_encoder()
                    self.processor.cleanup_decoder()
                    self.processor.init_decoder()

                    # Run send + recv concurrently
                    send_task = asyncio.create_task(self._send_task(ws, frames, self.processor))
                    recv_task = asyncio.create_task(self._recv_task(ws, self.processor, frame_callback))

                    # Wait until either finishes (e.g. frames end, remote closes…)
                    done, pending = await asyncio.wait(
                        [send_task, recv_task],
                        return_when=asyncio.FIRST_EXCEPTION,
                    )

                    # Propagate exceptions if any
                    for t in done:
                        exc = t.exception()
                        if exc:
                            raise exc  # noqa: TRY301

                    # Cancel leftover task if the other finished
                    for t in pending:
                        t.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await t

                    return  # Clean finish
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                attempt += 1
                await asyncio.sleep(self.reconnect_delay)
            finally:
                self.processor.cleanup_encoder()
                self.processor.cleanup_decoder()

    def start(
        self,
        frames: Generator[CvFrame, None, None],
        frame_callback: Callable[[CvFrame, int], None],
    ) -> None:
        asyncio.run(self._run_async(frames, frame_callback))
