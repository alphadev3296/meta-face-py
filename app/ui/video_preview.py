import tkinter as tk
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

from app.video.webcam import CvFrame


class VideoPreviewPanel(ttk.LabelFrame):
    """Main video preview panel"""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, text="Camera Preview", padding=5)

        self.preview_label = ttk.Label(
            self, text="Camera Preview", anchor="center", background="gray30", foreground="white"
        )
        self.preview_label.pack(fill="both", expand=True)

        # Placeholder for video feed
        self.cap = None
        self.running = False
        self.height = 500

    def show_frame(self, frame: CvFrame) -> None:
        # Convert BGR (OpenCV) -> RGB (Pillow)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Resize frame
        ratio = frame.shape[1] / frame.shape[0]
        resized_frame = cv2.resize(
            frame,
            (int(self.height * ratio), self.height),
            interpolation=cv2.INTER_AREA,
        )

        # Convert to PIL Image
        img = Image.fromarray(resized_frame)

        # Convert to ImageTk PhotoImage
        imgtk = ImageTk.PhotoImage(image=img)

        # Update preview
        self.preview_label.config(image=imgtk)
        self.preview_label.image = imgtk  # type: ignore  # noqa: PGH003
