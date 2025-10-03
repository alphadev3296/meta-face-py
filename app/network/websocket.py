import asyncio
from collections.abc import Callable, Generator
from typing import Optional

import av
import numpy as np
import websockets
from loguru import logger


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
        self.codec: Optional[av.CodecContext] = None
        self.consecutive_decode_errors = 0
        self.max_consecutive_errors = 10  # Reset decoder after this many consecutive errors

    def _init_decoder(self) -> None:
        """Initialize H.264 decoder using PyAV."""
        try:
            if self.codec is not None:
                self._cleanup_decoder()
            self.codec = av.CodecContext.create("h264", "r")
            # Set decoder options for better error handling
            self.codec.thread_type = "AUTO"  # Enable multi-threading
            self.codec.thread_count = 0  # Auto-detect thread count
            # Skip processing of frames with errors
            self.codec.skip_frame = "DEFAULT"
            logger.info("H.264 decoder initialized")
            self.consecutive_decode_errors = 0  # Reset error counter
        except Exception as e:
            logger.error(f"Failed to initialize H.264 decoder: {e}")
            raise

    def _decode_frame(self, packet_data: bytes) -> list[np.ndarray]:
        """
        Decode H.264 packet to video frame(s).
        Handles broken/corrupted frames gracefully.

        Args:
            packet_data (bytes): Raw H.264 encoded data

        Returns:
            list[np.ndarray]: List of decoded frames as numpy arrays (RGB format)
        """
        frames = []
        if not packet_data:
            return frames

        try:
            if self.codec is None:
                logger.error("Decoder not initialized")
                return frames

            # Validate minimum packet size (H.264 NAL unit header is at least 4 bytes)
            if len(packet_data) < 4:
                logger.warning(f"Packet too small ({len(packet_data)} bytes), likely corrupted")
                self.consecutive_decode_errors += 1
                return frames

            packet = av.Packet(packet_data)

            try:
                decoded_frames = self.codec.decode(packet)
                # Successful decode - reset error counter
                self.consecutive_decode_errors = 0
            except av.AVError as e:
                # Broken frame - try to recover by continuing
                self.consecutive_decode_errors += 1
                logger.warning(f"Broken frame detected (error #{self.consecutive_decode_errors}): {e}")

                # If too many consecutive errors, reinitialize decoder
                if self.consecutive_decode_errors >= self.max_consecutive_errors:
                    logger.error(
                        f"Too many consecutive decode errors ({self.consecutive_decode_errors}), reinitializing decoder..."
                    )
                    try:
                        self._init_decoder()
                        self.consecutive_decode_errors = 0
                    except Exception as reinit_error:
                        logger.error(f"Failed to reinitialize decoder: {reinit_error}")
                else:
                    # Try to flush decoder to reset state
                    try:
                        self.codec.decode(None)
                    except Exception:
                        pass
                return frames

            for frame in decoded_frames:
                try:
                    img = frame.to_ndarray(format="rgb24")
                    # Validate frame dimensions
                    if img.shape[0] <= 0 or img.shape[1] <= 0:
                        logger.warning(f"Invalid frame dimensions: {img.shape}")
                        continue
                    frames.append(img)
                    logger.debug(f"Decoded frame: {img.shape}")
                except Exception as e:
                    logger.warning(f"Error converting frame to array: {e}")
                    continue

        except av.AVError as e:
            self.consecutive_decode_errors += 1
            logger.error(f"AV error decoding frame: {e}")
        except Exception as e:
            self.consecutive_decode_errors += 1
            logger.error(f"Unexpected error decoding frame: {e}")

        return frames

    def _cleanup_decoder(self) -> None:
        """Flush and cleanup decoder."""
        try:
            if self.codec:
                # Flush remaining frames
                try:
                    remaining = self.codec.decode(None)
                    if remaining:
                        logger.info(f"Flushed {len(remaining)} remaining frames")
                except Exception as e:
                    logger.warning(f"Error during decoder flush: {e}")
                self.codec = None
        except Exception as e:
            logger.error(f"Error cleaning up decoder: {e}")

    async def send_and_receive_stream(
        self,
        byte_stream: Generator[bytes, None, None],
        frame_callback: Callable[[np.ndarray, int], None],
        status_callback: Optional[Callable[[str], None]] = None,
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
                    self._init_decoder()

                    async def send_task():
                        """Task to send video packets."""
                        nonlocal send_complete, send_error
                        try:
                            packet_count = 0
                            for packet in byte_stream:
                                if not packet:  # Skip empty packets
                                    continue
                                await ws.send(packet)
                                packet_count += 1
                                logger.debug(f"Sent packet {packet_count}: {len(packet)} bytes")
                                # Small delay to prevent overwhelming the connection
                                if packet_count % 30 == 0:  # Every ~1 second at 30fps
                                    await asyncio.sleep(0.001)
                            logger.info(f"Finished sending all packets (total: {packet_count})")
                            send_complete = True
                        except StopIteration:
                            logger.info("Generator exhausted")
                            send_complete = True
                        except websockets.exceptions.ConnectionClosed as e:
                            logger.warning(f"Connection closed during send: {e}")
                            send_error = e
                        except Exception as e:
                            logger.error(f"Error in send task: {e}")
                            send_error = e
                            raise

                    async def receive_task():
                        """Task to receive and decode video packets."""
                        nonlocal frame_count, receive_complete, receive_error
                        try:
                            packet_count = 0
                            async for message in ws:
                                if isinstance(message, bytes):
                                    packet_count += 1
                                    logger.debug(f"Received packet {packet_count}: {len(message)} bytes")
                                    frames = self._decode_frame(message)

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
                            receive_error = e
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

                    self._cleanup_decoder()
                    return

            except (OSError, websockets.exceptions.WebSocketException) as e:
                msg = f"WebSocket error: {e}. Retrying in {self.reconnect_delay}s..."
                logger.error(msg)
                if status_callback:
                    status_callback(msg)

                self._cleanup_decoder()
                attempt += 1
                if self.max_retries == -1 or attempt < self.max_retries:
                    await asyncio.sleep(self.reconnect_delay)

            except Exception as e:
                msg = f"Unexpected error: {e}"
                logger.error(msg, exc_info=True)  # Include stack trace
                if status_callback:
                    status_callback(msg)
                self._cleanup_decoder()
                raise

        msg = "Max retries exceeded. Bidirectional stream failed."
        logger.error(msg)
        if status_callback:
            status_callback(msg)
        raise ConnectionError(msg)
