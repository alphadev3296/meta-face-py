import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from app.schema.app_data import AppData
from app.schema.camera_resolution import CAMERA_RESOLUTIONS, CameraResolution
from app.video.webcam import Webcam


class CameraPanel(ttk.LabelFrame):
    """Camera configuration panel"""

    def __init__(
        self,
        parent: ttk.Frame,
        status_callback: Callable[[str], None],
        app_data: AppData,
    ) -> None:
        super().__init__(parent, text="Camera", padding=5)

        self.app_data = app_data
        self.status_callback = status_callback

        # Camera selection
        webcam_list = Webcam.list_webcams()
        ttk.Label(self, text="Camera:").grid(row=0, column=0, sticky="w", pady=2)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(
            self,
            textvariable=self.camera_var,
            values=[f"{dev[1]}" for dev in webcam_list],
            state="readonly",
            width=15,
        )
        self.camera_combo.grid(row=0, column=1, pady=2, sticky="ew")
        self.camera_combo.current(min(len(webcam_list) - 1, self.app_data.camera_id))
        self.camera_combo.bind("<<ComboboxSelected>>", self.on_camera_change)

        # Resolution selection
        ttk.Label(self, text="Resolution:").grid(row=1, column=0, sticky="w", pady=2)
        self.resolution_var = tk.StringVar()
        self.resolution_combo = ttk.Combobox(
            self,
            textvariable=self.resolution_var,
            values=[
                f"{cr.value} ({CAMERA_RESOLUTIONS[cr][0]}x{CAMERA_RESOLUTIONS[cr][1]})" for cr in list(CameraResolution)
            ],
            state="readonly",
            width=15,
        )
        self.resolution_combo.grid(row=1, column=1, pady=2, sticky="ew")
        self.resolution_combo.current(list(CameraResolution).index(self.app_data.resolution))
        self.resolution_combo.bind("<<ComboboxSelected>>", self.on_resolution_change)

        # FPS selection
        ttk.Label(self, text="FPS:").grid(row=2, column=0, sticky="w", pady=2)
        self.fps_var = tk.StringVar()
        self.fps_combo = ttk.Combobox(
            self, textvariable=self.fps_var, values=["5", "10", "25"], state="readonly", width=15
        )
        self.fps_combo.grid(row=2, column=1, pady=2, sticky="ew")
        self.fps_combo.set(str(self.app_data.fps))
        self.fps_combo.bind("<<ComboboxSelected>>", self.on_fps_change)

        self.columnconfigure(1, weight=1)

    def on_camera_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Camera changed to: {self.camera_var.get()}")
        self.app_data.camera_id = self.camera_combo.current()

    def on_resolution_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Resolution set to: {self.resolution_var.get()}")
        self.app_data.resolution = list(CameraResolution)[self.resolution_combo.current()]

    def on_fps_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"FPS set to: {self.fps_var.get()}")
        self.app_data.fps = int(self.fps_var.get())
