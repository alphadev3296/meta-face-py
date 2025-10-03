import asyncio
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING

import websockets
from loguru import logger

from app.video.h264 import H264VideoProcessor
from app.video.webcam import CvFrame

if TYPE_CHECKING:
    import av


class WebSocketVideoClient:
    def __init__(self, uri: str, reconnect_delay: int = 5, max_retries: int = 3) -> None:
        """
        Bidirectional WebSocket client for sending/receiving H.264 video streams.

        Args:
            uri (str): WebSocket server URI, e.g. "ws://localhost:8000/ws/video"
            reconnect_delay (int): Seconds to wait between reconnect attempts.
            max_retries (int): How many times to retry before giving up (-1 = infinite).
        """
        self.uri = uri
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries
        self.codec: av.CodecContext | None = None
        self.consecutive_decode_errors = 0
        self.max_consecutive_errors = 10  # Reset decoder after this many consecutive errors
        self.processor = H264VideoProcessor()

    async def send_and_receive_stream(
        self,
        frames: Generator[CvFrame, None, None],
        frame_callback: Callable[[CvFrame, int], None],
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        """
        Bidirectional: Send H264 stream and receive processed stream on single connection.

        Args:
            byte_stream (Generator[bytes]): yields byte packets to send
            frame_callback (Callable): Called with (frame, frame_number) for received frames
            status_callback (Callable, optional): Called with status messages
        """
        attempt = 0

        while self.max_retries == -1 or attempt < self.max_retries:
            frame_count = 0
            send_complete = False
            receive_complete = False
            send_error = None
            receive_error = None

            try:
                logger.info(f"Connecting to {self.uri} (attempt {attempt + 1})")

                async with websockets.connect(
                    self.uri,
                    max_size=None,
                    ping_interval=20,  # Send ping every 20 seconds
                    ping_timeout=10,  # Wait 10 seconds for pong
                    close_timeout=10,  # Wait 10 seconds for close handshake
                ) as ws:
                    msg = "WebSocket connection established for bidirectional streaming."
                    logger.info(msg)
                    if status_callback:
                        status_callback(msg)

                    # Initialize decoder for receiving
                    self.processor.init_decoder()

                    async def send_task() -> None:
                        """Task to send video packets."""
                        nonlocal send_complete, send_error
                        try:
                            packet_count = 0
                            for frame in frames:
                                # Initialize encoder on first frame
                                if not self.processor.encoder_initialized:
                                    self.processor.init_encoder(frame.shape[1], frame.shape[0])

                                encoded_packets = self.processor.encode_frame(frame)
                                for packet in encoded_packets:
                                    if not packet:  # Skip empty packets
                                        continue
                                    try:
                                        await ws.send(packet)
                                        packet_count += 1
                                        logger.debug(f"Sent packet {packet_count}: {len(packet)} bytes")
                                        logger.debug(f"Sent packet {packet_count}: {len(frame)} bytes")
                                        # Small delay to prevent overwhelming the connection
                                        if packet_count % 30 == 0:  # Every ~1 second at 30fps
                                            await asyncio.sleep(0.001)
                                    except StopIteration:
                                        logger.info("Generator exhausted")
                                        send_complete = True
                                    except websockets.exceptions.ConnectionClosed:
                                        logger.warning("Connection closed while sending packet")
                                        raise
                                    except Exception as e:
                                        logger.error(f"Error sending packet: {e}")
                                        raise

                            logger.info(f"Finished sending all packets (total: {packet_count})")
                            send_complete = True

                        except Exception as e:
                            logger.error(f"Error in send task: {e}")
                            send_error = e
                            raise

                    async def receive_task() -> None:
                        """Task to receive and decode video packets."""
                        nonlocal frame_count, receive_complete, receive_error
                        try:
                            packet_count = 0
                            async for message in ws:
                                if isinstance(message, bytes):
                                    packet_count += 1
                                    logger.debug(f"Received packet {packet_count}: {len(message)} bytes")
                                    frames = self.processor.decode_frame(message)

                                    for frame in frames:
                                        try:
                                            frame_callback(frame, frame_count)
                                            frame_count += 1
                                        except Exception as e:
                                            logger.error(f"Error in frame callback: {e}")
                                else:
                                    logger.warning(f"Received non-binary message: {message}")
                            logger.info(f"Finished receiving. Total frames: {frame_count}")
                            receive_complete = True
                        except websockets.exceptions.ConnectionClosed as e:
                            logger.info(f"Connection closed during receive: {e}")
                            receive_complete = True
                            receive_error = e
                        except Exception as e:
                            logger.error(f"Error in receive task: {e}")
                            receive_error = e  # type: ignore  # noqa: PGH003
                            raise

                    # Run send and receive concurrently
                    try:
                        await asyncio.gather(
                            send_task(),
                            receive_task(),
                            return_exceptions=False,  # Propagate exceptions
                        )
                    except Exception as e:
                        logger.error(f"Error in bidirectional tasks: {e}")
                        # Check which task failed
                        if send_error:
                            logger.error(f"Send task error: {send_error}")
                        if receive_error:
                            logger.error(f"Receive task error: {receive_error}")
                        raise

                    msg = f"Bidirectional stream complete. Frames decoded: {frame_count}"
                    logger.info(msg)
                    if status_callback:
                        status_callback(msg)

                    return

            except (OSError, websockets.exceptions.WebSocketException) as e:
                msg = f"WebSocket error: {e}. Retrying in {self.reconnect_delay}s..."
                logger.error(msg)
                if status_callback:
                    status_callback(msg)

                attempt += 1
                if self.max_retries == -1 or attempt < self.max_retries:
                    await asyncio.sleep(self.reconnect_delay)

            except Exception as e:
                msg = f"Unexpected error: {e}"
                logger.error(msg, exc_info=True)  # Include stack trace
                if status_callback:
                    status_callback(msg)
                raise

            finally:
                self.processor.cleanup()

        msg = "Max retries exceeded. Bidirectional stream failed."
        logger.error(msg)
        if status_callback:
            status_callback(msg)
        raise ConnectionError(msg)
