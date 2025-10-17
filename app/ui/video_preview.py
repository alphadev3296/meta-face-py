import tkinter as tk
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

from app.media.webcam import CvFrame
from app.schema.app_data import AppConfig


class VideoPanel(ttk.Frame):
    """Main video preview panel"""

    def __init__(self, parent: tk.Tk, app_cfg: AppConfig) -> None:
        super().__init__(parent)

        self.app_cfg = app_cfg

        # Configure grid rows and columns
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Camera view
        self.camera_frame = ttk.LabelFrame(self, text="Camera View", padding=5)
        self.camera_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.camera_frame.rowconfigure(0, weight=0)
        self.camera_frame.rowconfigure(1, weight=1)
        self.camera_frame.columnconfigure(0, weight=1)

        self.show_camera_var = tk.BooleanVar(value=self.app_cfg.show_camera)
        self.show_camera_cb = ttk.Checkbutton(
            self.camera_frame,
            text="Show Camera",
            variable=self.show_camera_var,
            command=self.handle_show_camera_toggle,
        )
        self.show_camera_cb.grid(row=0, column=0, sticky="w", pady=2)

        self.camera_stream_canvas = tk.Canvas(
            self.camera_frame,
            background="gray30",
            highlightthickness=0,
        )
        self.camera_stream_canvas.grid(row=1, column=0, sticky="nsew")

        # Processed view
        self.processed_frame = ttk.LabelFrame(self, text="Processed View", padding=5)
        self.processed_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.processed_stream_canvas = tk.Canvas(
            self.processed_frame,
            background="gray30",
            highlightthickness=0,
        )
        self.processed_stream_canvas.pack(fill="both", expand=True)

    def handle_show_camera_toggle(self) -> None:
        self.app_cfg.show_camera = self.show_camera_var.get()
        self.app_cfg.save()

    def show_processed_frame(self, frame: CvFrame) -> None:
        # Convert BGR (OpenCV) -> RGB (Pillow)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Target display size
        target_w = self.processed_stream_canvas.winfo_width()
        target_h = self.processed_stream_canvas.winfo_height()
        if target_w <= 1 or target_h <= 1:
            # Canvas not yet realized, skip this frame
            return

        # Compute scale ratio while preserving aspect ratio
        h, w = frame.shape[:2]
        ratio = min(target_w / w, target_h / h)
        new_w, new_h = int(w * ratio), int(h * ratio)

        resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Convert to PIL Image
        img = Image.fromarray(resized_frame)

        # Convert to ImageTk PhotoImage
        imgtk = ImageTk.PhotoImage(image=img)

        # Update canvas
        self.processed_stream_canvas.delete("all")
        self.processed_stream_canvas.create_image(
            target_w // 2,
            target_h // 2,
            image=imgtk,
            anchor="center",
        )
        self.processed_stream_canvas.image = imgtk  # type: ignore  # noqa: PGH003 # keep reference

    def show_camera_frame(self, frame: CvFrame) -> None:
        if not self.app_cfg.show_camera:
            # Clear canvas
            self.camera_stream_canvas.delete("all")
            return

        # Convert BGR (OpenCV) -> RGB (Pillow)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Target display size
        target_w = self.camera_stream_canvas.winfo_width()
        target_h = self.camera_stream_canvas.winfo_height()
        if target_w <= 1 or target_h <= 1:
            # Canvas not yet realized, skip this frame
            return

        # Compute scale ratio while preserving aspect ratio
        h, w = frame.shape[:2]
        ratio = min(target_w / w, target_h / h)
        new_w, new_h = int(w * ratio), int(h * ratio)

        resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Convert to PIL Image
        img = Image.fromarray(resized_frame)

        # Convert to ImageTk PhotoImage
        imgtk = ImageTk.PhotoImage(image=img)

        # Update canvas
        self.camera_stream_canvas.delete("all")
        self.camera_stream_canvas.create_image(
            target_w // 2,
            target_h // 2,
            image=imgtk,
            anchor="center",
        )
        self.camera_stream_canvas.image = imgtk  # type: ignore  # noqa: PGH003 # keep reference
