import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

from app.schema.app_data import AppData
from app.video.webcam import CvFrame


class LocalVideoPanel(ttk.LabelFrame):
    """Local video preview panel"""

    def __init__(
        self,
        parent: ttk.Frame,
        status_callback: Callable[[str], None],
        app_data: AppData,
    ) -> None:
        super().__init__(parent, text="Camera Stream", padding=5)

        self.app_data = app_data
        self.status_callback = status_callback

        self.height = 100

        # Show/hide checkbox
        self.show_local_stream_var = tk.BooleanVar(value=self.app_data.show_local_video)
        self.show_local_stream_cb = ttk.Checkbutton(
            self,
            text="Show Camera Stream",
            variable=self.show_local_stream_var,
            command=self.on_show_local_stream_toggle,
        )
        self.show_local_stream_cb.grid(row=0, column=0, sticky="w", pady=2)

        # Camera view
        self.camera_view_frame = ttk.Frame(self, relief="sunken", borderwidth=1, height=self.height)
        self.camera_view_frame.grid(row=1, column=0, pady=5, sticky="ew")

        self.camera_view_label = ttk.Label(
            self.camera_view_frame, text="Camera Stream", anchor="center", background="gray20", foreground="white"
        )
        self.camera_view_label.pack(fill="both", expand=True)

        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        # Initial state
        self.on_show_local_stream_toggle()

    def on_show_local_stream_toggle(self) -> None:
        show_local_video = self.show_local_stream_var.get()
        self.app_data.show_local_video = show_local_video
        if show_local_video:
            self.camera_view_label.pack(fill="both", expand=True)
            self.status_callback("Local video preview shown")
        else:
            self.camera_view_label.pack_forget()
            self.status_callback("Local video preview hidden")

    def show_camera_frame(self, frame: CvFrame) -> None:
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
        self.camera_view_label.config(image=imgtk)
        self.camera_view_label.image = imgtk  # type: ignore  # noqa: PGH003
