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

        self._processed_img_id: int | None = None
        self._camera_img_id: int | None = None

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
        self.processed_frame.rowconfigure(0, weight=0)
        self.processed_frame.rowconfigure(1, weight=1)
        self.processed_frame.columnconfigure(0, weight=1)

        self.show_processed_var = tk.BooleanVar(value=True)
        self.show_processed_cb = ttk.Checkbutton(
            self.processed_frame,
            text="Show Processed",
            variable=self.show_processed_var,
            state="disabled",
        )
        self.show_processed_cb.grid(row=0, column=0, sticky="w", pady=2)

        self.processed_stream_canvas = tk.Canvas(
            self.processed_frame,
            background="gray30",
            highlightthickness=0,
        )
        self.processed_stream_canvas.grid(row=1, column=0, sticky="nsew")

    def handle_show_camera_toggle(self) -> None:
        self.app_cfg.show_camera = self.show_camera_var.get()
        self.app_cfg.save()

    def show_processed_frame(self, frame: CvFrame) -> None:
        # Convert OpenCV BGR -> RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        target_w = self.processed_stream_canvas.winfo_width()
        target_h = self.processed_stream_canvas.winfo_height()
        if target_w <= 1 or target_h <= 1:
            return

        h, w = frame.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Convert to ImageTk once per frame
        img = Image.fromarray(resized)
        imgtk = ImageTk.PhotoImage(image=img)

        # Only create the image once; then just update it
        if not hasattr(self, "_processed_img_id") or self._processed_img_id is None:
            # first time: create image item centered on canvas
            self._processed_img_id = self.processed_stream_canvas.create_image(
                target_w / 2,
                target_h / 2,
                image=imgtk,
                anchor="center",
            )
        else:
            # just update existing image
            self.processed_stream_canvas.itemconfig(self._processed_img_id, image=imgtk)

        self._processed_imgtk = imgtk

    def show_camera_frame(self, frame: CvFrame) -> None:
        if not self.app_cfg.show_camera:
            self.camera_stream_canvas.delete("all")
            self._camera_imgtk = None
            self._camera_img_id = None
            return

        # Convert OpenCV BGR -> RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        target_w = self.camera_stream_canvas.winfo_width()
        target_h = self.camera_stream_canvas.winfo_height()
        if target_w <= 1 or target_h <= 1:
            return

        h, w = frame.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Convert to ImageTk once per frame
        img = Image.fromarray(resized)
        imgtk = ImageTk.PhotoImage(image=img)

        # Only create the image once; then just update it
        if not hasattr(self, "_camera_img_id") or self._camera_img_id is None:
            # first time: create image item centered on canvas
            self._camera_img_id = self.camera_stream_canvas.create_image(
                target_w // 2,
                target_h // 2,
                image=imgtk,
                anchor="center",
            )
        else:
            # just update existing item
            self.camera_stream_canvas.itemconfig(self._camera_img_id, image=imgtk)

        # keep a reference or image will vanish
        self._camera_imgtk = imgtk
