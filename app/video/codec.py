from collections.abc import Generator
from fractions import Fraction

import av
import cv2

from app.video.webcam import CvFrame


class VideoCodec:
    @classmethod
    def encode_h264(
        cls,
        frames: Generator[CvFrame, None, None],
        width: int,
        height: int,
        fps: int,
    ) -> Generator[bytes, None, None]:
        codec = av.CodecContext.create("h264", "w")
        codec.width = width
        codec.height = height
        codec.time_base = Fraction(1, fps)
        codec.framerate = Fraction(fps, 1)
        codec.pix_fmt = "yuv420p"
        codec.gop_size = fps

        for fra in frames:
            frame = fra

            # Resize if needed
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))

            # Encode
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            av_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")  # type: ignore  # noqa: PGH003
            packets = codec.encode(av_frame)

            # Yield the encoded packets
            for packet in packets:
                yield bytes(packet)
