import asyncio
import contextlib
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor

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
        max_queue_size: int = 5,  # Small for low latency
        num_workers: int = 4,
    ) -> None:
        """
        High-performance concurrent WebSocket client for real-time video streaming.
        """
        self.uri = uri
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries
        self.max_queue_size = max_queue_size
        self.num_workers = num_workers
        self.processor = H264VideoProcessor()
        self.executor: ThreadPoolExecutor | None = None
        self._running = False

    def _get_executor(self) -> ThreadPoolExecutor:
        """Lazy initialization of executor."""
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=self.num_workers, thread_name_prefix="video_worker")
        return self.executor

    async def _send_task(
        self,
        ws: websockets.ClientConnection,
        frame_queue: asyncio.Queue[CvFrame | None],
    ) -> None:
        """Send frames from queue - truly independent task."""
        packet_count = 0
        loop = asyncio.get_running_loop()
        executor = self._get_executor()

        try:
            while self._running:
                try:
                    # Use timeout to allow periodic checks of _running flag
                    frame = await asyncio.wait_for(frame_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:  # noqa: UP041
                    continue

                if frame is None:  # Stop signal
                    logger.info("Send task received stop signal")
                    break

                # Initialize encoder if needed (do this in main thread, it's fast)
                if not self.processor.encoder_initialized:
                    self.processor.init_encoder(frame.shape[1], frame.shape[0])

                # Encode in thread pool - THIS IS THE KEY FIX
                # We need to ensure encode_frame is truly offloaded
                def encode_work() -> list[bytes]:
                    return list(self.processor.encode_frame(frame))  # noqa: B023

                packets = await loop.run_in_executor(executor, encode_work)

                # Send all packets WITHOUT await in between for max throughput
                send_coros = []
                for packet in packets:
                    if packet:
                        send_coros.append(ws.send(packet))
                        packet_count += 1

                # Send all packets concurrently
                if send_coros:
                    await asyncio.gather(*send_coros)

                frame_queue.task_done()

                # Yield control to event loop
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Send task cancelled")
            raise
        except Exception as e:
            logger.error(f"Send task error: {e}", exc_info=True)
            raise
        finally:
            logger.info(f"Send task finished. Total packets sent: {packet_count}")

    async def _recv_task(
        self,
        ws: websockets.ClientConnection,
        frame_callback: Callable[["CvFrame", int], None],
    ) -> None:
        """Receive and decode frames - truly independent task."""
        frame_count = 0
        loop = asyncio.get_running_loop()
        executor = self._get_executor()

        try:
            while self._running:
                try:
                    # Use timeout to allow checking _running flag
                    message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                except TimeoutError:
                    continue

                if isinstance(message, bytes):
                    # Decode in thread pool - CRITICAL for concurrency
                    def decode_work() -> list[CvFrame]:
                        return list(self.processor.decode_frame(message))  # noqa: B023

                    decoded_frames = await loop.run_in_executor(executor, decode_work)

                    # Process frames
                    for f in decoded_frames:
                        # Run callback in thread pool - CRITICAL if callback is slow
                        def callback_work() -> None:
                            frame_callback(f, frame_count)  # noqa: B023

                        # Fire and forget for max throughput
                        loop.run_in_executor(executor, callback_work)
                        frame_count += 1

                    # Yield control to event loop
                    await asyncio.sleep(0)
                else:
                    logger.warning(f"Received non-binary message: {message}")

        except asyncio.CancelledError:
            logger.info("Recv task cancelled")
            raise
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Recv task error: {e}", exc_info=True)
            raise
        finally:
            logger.info(f"Recv task finished. Total frames received: {frame_count}")

    async def _frame_producer(
        self,
        frames: Generator["CvFrame", None, None],
        frame_queue: asyncio.Queue[CvFrame | None],
    ) -> None:
        """
        Producer task - THE MOST CRITICAL FIX.
        Your generator is probably blocking (reading from camera/file).
        """
        loop = asyncio.get_running_loop()
        executor = self._get_executor()
        frame_count = 0

        try:
            while self._running:
                try:
                    # Get next frame in thread pool - THIS IS CRITICAL
                    # Your generator might be calling cv2.VideoCapture.read() which blocks!
                    def get_next_frame() -> CvFrame | None:
                        try:
                            return next(frames)
                        except StopIteration:
                            return None

                    frame = await loop.run_in_executor(executor, get_next_frame)

                    if frame is None:
                        logger.info(f"Frame generator exhausted after {frame_count} frames")
                        break

                    # Put in queue (with timeout to check _running flag)
                    try:
                        await asyncio.wait_for(frame_queue.put(frame), timeout=1.0)
                        frame_count += 1
                    except TimeoutError:
                        # Queue is full, drop frame for low latency
                        logger.warning(f"Queue full, dropping frame {frame_count}")
                        continue

                    # Yield control
                    await asyncio.sleep(0)

                except Exception as e:
                    logger.error(f"Error getting frame: {e}", exc_info=True)
                    break

            # Send stop signal
            await frame_queue.put(None)
            logger.info(f"Frame producer finished. Total frames: {frame_count}")

        except asyncio.CancelledError:
            logger.info("Frame producer cancelled")
            await frame_queue.put(None)
            raise
        except Exception as e:
            logger.error(f"Frame producer error: {e}", exc_info=True)
            await frame_queue.put(None)
            raise

    async def _run_async(
        self,
        frames: Generator["CvFrame", None, None],
        frame_callback: Callable[["CvFrame", int], None],
        jwt_token: str,
        photo: bytes,
    ) -> None:
        attempt = 0

        while self.max_retries == -1 or attempt < self.max_retries:
            self._running = True
            producer_task = None
            send_task = None
            recv_task = None

            try:
                # Configure WebSocket for high throughput
                async with websockets.connect(
                    self.uri,
                    max_size=None,  # No message size limit
                    ping_interval=20,
                    ping_timeout=10,
                    write_limit=2**20,  # 1MB write buffer
                ) as ws:
                    logger.info(f"Connected to WebSocket: {self.uri}")

                    # Send JWT token
                    await ws.send(jwt_token)

                    # Send photo
                    await ws.send(photo)

                    # Reset codec state
                    self.processor.cleanup_encoder()
                    self.processor.cleanup_decoder()
                    self.processor.init_decoder()

                    # Create queue - small size for low latency
                    frame_queue: asyncio.Queue[CvFrame | None] = asyncio.Queue(maxsize=self.max_queue_size)

                    # Create all tasks with explicit names
                    producer_task = asyncio.create_task(
                        self._frame_producer(frames, frame_queue), name="frame_producer"
                    )
                    send_task = asyncio.create_task(self._send_task(ws, frame_queue), name="send_task")
                    recv_task = asyncio.create_task(self._recv_task(ws, frame_callback), name="recv_task")

                    # Wait for first completion or exception
                    done, pending = await asyncio.wait(
                        [producer_task, send_task, recv_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Stop all tasks
                    self._running = False

                    # Check for exceptions in completed tasks
                    exception_occurred = False
                    for t in done:
                        exc = t.exception()
                        if exc:
                            logger.error(f"Task {t.get_name()} failed: {exc}", exc_info=exc)
                            exception_occurred = True

                    # Cancel remaining tasks gracefully
                    for t in pending:
                        logger.info(f"Cancelling task: {t.get_name()}")
                        t.cancel()

                    # Wait for cancellation with timeout
                    if pending:
                        await asyncio.wait(pending, timeout=5.0)

                    if exception_occurred:
                        msg = "One or more tasks failed"
                        raise RuntimeError(msg)  # noqa: TRY301

                    logger.info("All tasks completed successfully")
                    return  # Clean finish

            except asyncio.CancelledError:
                logger.info("Client cancelled")
                self._running = False
                raise
            except Exception as e:
                logger.error(f"WebSocket error (attempt {attempt + 1}): {e}", exc_info=True)
                self._running = False
                attempt += 1

                if self.max_retries == -1 or attempt < self.max_retries:
                    logger.info(f"Retrying in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    logger.error("Max retries reached")
                    raise
            finally:
                self._running = False

                # Ensure all tasks are cancelled
                for task in [producer_task, send_task, recv_task]:
                    if task and not task.done():
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await task

                # Cleanup codecs
                self.processor.cleanup_encoder()
                self.processor.cleanup_decoder()

    def start(
        self,
        frames: Generator[CvFrame, None, None],
        frame_callback: Callable[[CvFrame, int], None],
        jwt_token: str,
        photo: bytes,
    ) -> None:
        """Start the WebSocket client with true concurrent processing."""
        try:
            asyncio.run(self._run_async(frames, frame_callback, jwt_token, photo))
        finally:
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

    def stop(self) -> None:
        """Signal all tasks to stop."""
        self._running = False

    def __del__(self) -> None:
        """Cleanup executor on deletion."""
        if hasattr(self, "executor") and self.executor:
            self.executor.shutdown(wait=False)
