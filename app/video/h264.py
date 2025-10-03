import contextlib
from fractions import Fraction

import av
import cv2
from loguru import logger

from app.video.webcam import CvFrame


class H264VideoProcessor:
    """Process H.264 video: decode, convert to grayscale, re-encode."""

    def __init__(self) -> None:
        self.decoder: av.CodecContext | None = None
        self.encoder: av.CodecContext | None = None
        self.frame_count = 0
        self.encoder_initialized = False
        self.consecutive_decode_errors = 0
        self.max_consecutive_errors = 10  # Reset decoder after this many errors

    def init_decoder(self) -> None:
        """Initialize H.264 decoder."""
        try:
            if self.decoder is not None:
                self.cleanup_decoder()
            self.decoder = av.CodecContext.create("h264", "r")
            # Set decoder options for better error handling
            self.decoder.thread_type = "AUTO"
            self.decoder.thread_count = 0
            self.decoder.skip_frame = "DEFAULT"
            logger.info("Decoder initialized")
            self.consecutive_decode_errors = 0  # Reset error counter
        except Exception as e:
            logger.error(f"Failed to initialize decoder: {e}")
            raise

    def init_encoder(self, width: int, height: int, fps: int = 30) -> None:
        """Initialize H.264 encoder for grayscale output."""
        try:
            if self.encoder is not None:
                self.cleanup_encoder()

            self.encoder = av.CodecContext.create("h264", "w")
            self.encoder.width = width
            self.encoder.height = height
            self.encoder.pix_fmt = "yuv420p"
            self.encoder.time_base = Fraction(1, fps)
            self.encoder.framerate = Fraction(fps, 1)
            self.encoder.bit_rate = 2000000  # 2 Mbps
            self.encoder.options = {"preset": "ultrafast", "tune": "zerolatency"}
            self.encoder_initialized = True
            logger.info(f"Encoder initialized: {width}x{height} @ {fps}fps")
        except Exception as e:
            logger.error(f"Failed to initialize encoder: {e}")
            raise

    def decode_frame(self, packet_data: bytes) -> list[CvFrame]:
        """
        Decode H.264 packet to frames.
        Handles broken/corrupted frames gracefully.
        """
        frames: list[CvFrame] = []
        if not packet_data:
            return frames

        try:
            if self.decoder is None:
                logger.error("Decoder not initialized")
                return frames

            # Validate minimum packet size
            if len(packet_data) < 4:  # noqa: PLR2004
                logger.warning(f"Packet too small ({len(packet_data)} bytes), likely corrupted")
                self.consecutive_decode_errors += 1
                return frames

            packet = av.Packet(packet_data)

            try:
                decoded_frames = self.decoder.decode(packet)  # type: ignore  # noqa: PGH003
                # Successful decode - reset error counter
                self.consecutive_decode_errors = 0
            except av.AVError as e:  # type: ignore  # noqa: PGH003
                # Broken frame - try to recover
                self.consecutive_decode_errors += 1
                logger.warning(f"Broken frame detected (error #{self.consecutive_decode_errors}): {e}")

                # If too many consecutive errors, reinitialize decoder
                if self.consecutive_decode_errors >= self.max_consecutive_errors:
                    logger.error(
                        f"Too many consecutive decode errors ({self.consecutive_decode_errors}), reinitializing decoder..."  # noqa: E501
                    )
                    try:
                        self.init_decoder()
                        self.consecutive_decode_errors = 0
                    except Exception as reinit_error:
                        logger.error(f"Failed to reinitialize decoder: {reinit_error}")
                else:
                    # Flush decoder to reset state
                    with contextlib.suppress(Exception):
                        self.decoder.decode(None)  # type: ignore  # noqa: PGH003
                return frames

            for frame in decoded_frames:
                try:
                    img = frame.to_ndarray(format="rgb24")
                    # Validate frame dimensions
                    if img.shape[0] <= 0 or img.shape[1] <= 0:
                        logger.warning(f"Invalid frame dimensions: {img.shape}")
                        continue
                    frames.append(img)
                    self.frame_count += 1
                    logger.debug(f"Decoded frame {self.frame_count}: {img.shape}")
                except Exception as e:
                    logger.warning(f"Error converting frame to array: {e}")
                    continue

        except av.AVError as e:  # type: ignore  # noqa: PGH003
            self.consecutive_decode_errors += 1
            logger.error(f"AV error decoding: {e}")
        except Exception as e:
            self.consecutive_decode_errors += 1
            logger.error(f"Unexpected error decoding: {e}")

        return frames

    def process_to_grayscale(self, frame_rgb: CvFrame) -> CvFrame:
        """Convert RGB frame to grayscale (3-channel for H.264)."""
        try:
            if frame_rgb is None or frame_rgb.size == 0:
                logger.error("Empty frame received for grayscale conversion")
                return frame_rgb

            # Convert to grayscale
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            # Convert back to 3-channel (required for H.264 encoding)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        except Exception as e:
            logger.error(f"Error converting to grayscale: {e}")
            return frame_rgb

    def encode_frame(self, frame_rgb: CvFrame) -> list[bytes]:
        """Encode RGB frame to H.264 packets."""
        packets: list[bytes] = []
        try:
            if self.encoder is None or not self.encoder_initialized:
                logger.error("Encoder not initialized")
                return packets

            if frame_rgb is None or frame_rgb.size == 0:
                logger.error("Empty frame for encoding")
                return packets

            # Create PyAV frame
            av_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            av_frame.pts = self.frame_count

            # Encode
            encoded_packets = self.encoder.encode(av_frame)  # type: ignore  # noqa: PGH003

            for pkt in encoded_packets:
                packets.append(bytes(pkt))
                logger.debug(f"Encoded packet: {len(packets[-1])} bytes")

        except av.AVError as e:  # type: ignore  # noqa: PGH003
            logger.error(f"AV error encoding: {e}")
        except Exception as e:
            logger.error(f"Unexpected error encoding: {e}")

        return packets

    def flush_encoder(self) -> list[bytes]:
        """Flush remaining packets from encoder."""
        packets: list[bytes] = []
        try:
            if self.encoder is not None and self.encoder_initialized:
                encoded_packets = self.encoder.encode(None)  # type: ignore  # noqa: PGH003
                for pkt in encoded_packets:
                    packets.append(bytes(pkt))  # noqa: PERF401
                logger.info(f"Flushed {len(packets)} packets from encoder")
        except Exception as e:
            logger.error(f"Error flushing encoder: {e}")
        return packets

    def cleanup_decoder(self) -> None:
        """Cleanup decoder resources."""
        try:
            if self.decoder:
                # Flush decoder
                with contextlib.suppress(Exception):
                    self.decoder.decode(None)  # type: ignore  # noqa: PGH003
                self.decoder = None
        except Exception as e:
            logger.error(f"Error cleaning up decoder: {e}")

    def cleanup_encoder(self) -> None:
        """Cleanup encoder resources."""
        try:
            if self.encoder:
                # Flush encoder
                with contextlib.suppress(Exception):
                    self.encoder.encode(None)  # type: ignore  # noqa: PGH003
                self.encoder = None
                self.encoder_initialized = False
        except Exception as e:
            logger.error(f"Error cleaning up encoder: {e}")

    def cleanup(self) -> None:
        """Cleanup all resources."""
        self.cleanup_decoder()
        self.cleanup_encoder()
        self.frame_count = 0
