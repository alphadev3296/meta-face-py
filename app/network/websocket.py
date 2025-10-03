import asyncio
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

    async def _run_async(
        self,
        frames: Generator[CvFrame, None, None],
        frame_callback: Callable[[CvFrame, int], None],
    ) -> None:
        attempt = 0
        while self.max_retries == -1 or attempt < self.max_retries:
            try:
                async with websockets.connect(self.uri, max_size=None) as ws:
                    logger.info(f"Connected to WebSocket: {self.uri}")

                    self.processor.cleanup_encoder()
                    self.processor.cleanup_decoder()
                    self.processor.init_decoder()

                    frame_count = 0
                    packet_count = 0

                    for frame in frames:
                        # Initialize encoder if not done
                        if not self.processor.encoder_initialized:
                            self.processor.init_encoder(frame.shape[1], frame.shape[0])

                        # Encode frame (might produce multiple packets)
                        for packet in self.processor.encode_frame(frame):
                            if packet:
                                await ws.send(packet)
                                packet_count += 1
                                logger.debug(f"Sent packet {packet_count} ({len(packet)} bytes)")

                        # Wait for a response packet from server
                        message = await ws.recv()
                        if isinstance(message, bytes):
                            decoded_frames = self.processor.decode_frame(message)
                            for f in decoded_frames:
                                frame_callback(f, frame_count)
                                frame_count += 1
                        else:
                            logger.warning(f"Received non-binary message: {message}")

                    logger.info(f"Stream finished. Sent packets={packet_count}, Received frames={frame_count}")
                    return
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
