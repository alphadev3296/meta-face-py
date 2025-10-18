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
        self._last_camera_frame: CvFrame | None = None
        self._last_processed_frame: CvFrame | None = None

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

        # Bind resize events
        self.camera_stream_canvas.bind("<Configure>", self._on_camera_resize)
        self.processed_stream_canvas.bind("<Configure>", self._on_processed_resize)

    # ---- Event handlers ----
    def _on_camera_resize(self, _event) -> None:  # noqa: ANN001
        """When resized, re-render the last shown camera frame if available."""
        self.camera_stream_canvas.delete("all")
        self._camera_img_id = None
        if self._last_camera_frame is not None:
            self.show_camera_frame(self._last_camera_frame)

    def _on_processed_resize(self, _event) -> None:  # noqa: ANN001
        """When resized, re-render the last shown processed frame if available."""
        self.processed_stream_canvas.delete("all")
        self._processed_img_id = None
        if self._last_processed_frame is not None:
            self.show_processed_frame(self._last_processed_frame)

    def handle_show_camera_toggle(self) -> None:
        self.app_cfg.show_camera = self.show_camera_var.get()
        self.app_cfg.save()

    # ---- Display methods ----
    def show_processed_frame(self, frame: CvFrame) -> None:
        self._last_processed_frame = frame  # cache last frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        target_w = self.processed_stream_canvas.winfo_width()
        target_h = self.processed_stream_canvas.winfo_height()
        if target_w <= 1 or target_h <= 1:
            return

        h, w = frame_rgb.shape[:2]
        scale = min(target_w / w, target_h / h)
        resized = cv2.resize(frame_rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        imgtk = ImageTk.PhotoImage(Image.fromarray(resized))

        if self._processed_img_id is None:
            self._processed_img_id = self.processed_stream_canvas.create_image(
                target_w / 2, target_h / 2, image=imgtk, anchor="center"
            )
        else:
            self.processed_stream_canvas.itemconfig(self._processed_img_id, image=imgtk)

        self._processed_imgtk = imgtk  # keep ref

    def show_camera_frame(self, frame: CvFrame) -> None:
        if not self.app_cfg.show_camera:
            self.camera_stream_canvas.delete("all")
            self._camera_img_id = None
            self._camera_imgtk = None
            return

        self._last_camera_frame = frame  # cache last frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        target_w = self.camera_stream_canvas.winfo_width()
        target_h = self.camera_stream_canvas.winfo_height()
        if target_w <= 1 or target_h <= 1:
            return

        h, w = frame_rgb.shape[:2]
        scale = min(target_w / w, target_h / h)
        resized = cv2.resize(frame_rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        imgtk = ImageTk.PhotoImage(Image.fromarray(resized))

        if self._camera_img_id is None:
            self._camera_img_id = self.camera_stream_canvas.create_image(
                target_w / 2, target_h / 2, image=imgtk, anchor="center"
            )
        else:
            self.camera_stream_canvas.itemconfig(self._camera_img_id, image=imgtk)

        self._camera_imgtk = imgtk
