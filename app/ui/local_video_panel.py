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
        super().__init__(parent, text="Local Video", padding=5)

        self.app_data = app_data
        self.status_callback = status_callback

        self.height = 100

        # Show/hide checkbox
        self.show_var = tk.BooleanVar(value=self.app_data.show_local_video)
        self.show_cb = ttk.Checkbutton(
            self, text="Show Local Video", variable=self.show_var, command=self.on_show_toggle
        )
        self.show_cb.grid(row=0, column=0, sticky="w", pady=2)

        # Video preview
        self.preview_frame = ttk.Frame(self, relief="sunken", borderwidth=1, height=self.height)
        self.preview_frame.grid(row=1, column=0, pady=5, sticky="ew")

        self.preview_label = ttk.Label(
            self.preview_frame, text="Local Preview", anchor="center", background="gray20", foreground="white"
        )
        self.preview_label.pack(fill="both", expand=True)

        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        # Initial state
        self.on_show_toggle()

    def on_show_toggle(self) -> None:
        show_local_video = self.show_var.get()
        self.app_data.show_local_video = show_local_video
        if show_local_video:
            self.preview_label.pack(fill="both", expand=True)
            self.status_callback("Local video preview shown")
        else:
            self.preview_label.pack_forget()
            self.status_callback("Local video preview hidden")

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
