import threading
import time

import numpy as np
import sounddevice as sd
from loguru import logger


class AudioDelay:
    def __init__(
        self,
        input_device_id: int,
        output_device_id: int,
        delay_secs: float,
        sample_rate: int = 44100,
        channels: int = 1,
    ) -> None:
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id
        self.delay_secs = delay_secs if delay_secs > 0 else 0.05
        self.sample_rate = sample_rate
        self.channels = channels

        self.buffer_size = int(self.delay_secs * self.sample_rate * self.channels)
        self.delay_buffer = np.zeros(self.buffer_size)
        self.buffer_index = 0

        self.delay_thread: threading.Thread | None = None
        self.delay_thread_stop_event = threading.Event()

    def _audio_callback(self, indata, outdata, frames, time, status) -> None:  # type:ignore  # noqa: ANN001, ARG002, PGH003
        if status:
            logger.debug(f"Status: {status}")

        # Flatten input to 1D array
        input_audio = indata.flatten()

        # Process each frame
        delayed_audio = np.zeros(frames * self.channels)
        for i in range(frames * self.channels):
            # Read delayed audio from buffer
            delayed_audio[i] = self.delay_buffer[self.buffer_index]

            # Write new audio to buffer
            self.delay_buffer[self.buffer_index] = input_audio[i]

            # Move to next position (circular)
            self.buffer_index = (self.buffer_index + 1) % self.buffer_size

        # Output delayed audio
        outdata[:] = delayed_audio.reshape(-1, self.channels)

    def open(self) -> None:
        self.delay_thread_stop_event.clear()
        self.delay_thread = threading.Thread(target=self._delay_loop, daemon=True)
        self.delay_thread.start()

    def close(self) -> None:
        if self.delay_thread is not None:
            if not self.delay_thread_stop_event.is_set():
                self.delay_thread_stop_event.set()
            self.delay_thread.join()
            self.delay_thread = None

    def _delay_loop(self) -> None:
        while not self.delay_thread_stop_event.is_set():
            try:
                with sd.Stream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    device=(self.input_device_id, self.output_device_id),
                    callback=self._audio_callback,
                ):
                    while True:
                        time.sleep(1.0)
            except Exception as e:
                logger.error(f"Error streaming audio: {e}")

            time.sleep(0.1)
