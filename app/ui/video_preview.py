import tkinter as tk
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

from app.video.webcam import CvFrame


class VideoPreviewPanel(ttk.LabelFrame):
    """Main video preview panel"""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, text="Camera Preview", padding=5)

        self.processed_stream_label = ttk.Label(
            self, text="Processed Stream", anchor="center", background="gray30", foreground="white"
        )
        self.processed_stream_label.pack(fill="both", expand=True)

    def show_processed_frame(self, frame: CvFrame) -> None:
        # Convert BGR (OpenCV) -> RGB (Pillow)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Target display size
        target_w = self.processed_stream_label.winfo_width()
        target_h = self.processed_stream_label.winfo_height()
        if target_w == 1 and target_h == 1:
            # On the first call, size may still be 1, wait until widget is realized
            target_w, target_h = 640, 480  # fallback default

        # Compute scale ratio while preserving aspect ratio
        h, w = frame.shape[:2]
        ratio = min(target_w / w, target_h / h)
        new_w, new_h = int(w * ratio), int(h * ratio)

        resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Convert to PIL Image
        img = Image.fromarray(resized_frame)

        # Convert to ImageTk PhotoImage
        imgtk = ImageTk.PhotoImage(image=img)

        # Update preview
        self.processed_stream_label.config(image=imgtk)
        self.processed_stream_label.image = imgtk  # type: ignore  # noqa: PGH003 # keep reference
