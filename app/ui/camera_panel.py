import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from app.schema.app_data import AppConfig, StreamingStatus
from app.schema.camera_resolution import CAMERA_RESOLUTIONS, CameraResolution
from app.video.webcam import Webcam


class CameraPanel(ttk.LabelFrame):
    """Camera configuration panel"""

    def __init__(
        self,
        parent: ttk.Frame,
        status_callback: Callable[[str], None],
        app_data: AppConfig,
        reconnect_camera_fn: Callable[[], None],
    ) -> None:
        super().__init__(parent, text="Camera", padding=5)

        self.app_cfg = app_data
        self.status_callback = status_callback
        self.reconnect_camera_callback = reconnect_camera_fn

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
        self.camera_combo.current(min(len(webcam_list) - 1, self.app_cfg.camera_id))
        self.camera_combo.bind("<<ComboboxSelected>>", self.handle_camera_change)

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
        self.resolution_combo.current(list(CameraResolution).index(self.app_cfg.resolution))
        self.resolution_combo.bind("<<ComboboxSelected>>", self.handle_resolution_change)

        # FPS selection
        ttk.Label(self, text="FPS:").grid(row=2, column=0, sticky="w", pady=2)
        self.fps_var = tk.StringVar()
        self.fps_combo = ttk.Combobox(
            self, textvariable=self.fps_var, values=["5", "10", "25"], state="readonly", width=15
        )
        self.fps_combo.grid(row=2, column=1, pady=2, sticky="ew")
        self.fps_combo.set(str(self.app_cfg.fps))
        self.fps_combo.bind("<<ComboboxSelected>>", self.handle_fps_change)

        # Zoom slider
        ttk.Label(self, text="Zoom:").grid(row=3, column=0, sticky="w", pady=2)
        self.zoom_var = tk.DoubleVar(value=getattr(self.app_cfg, "zoom", 1.0))
        self.zoom_slider = ttk.Scale(
            self,
            from_=1.0,
            to=4.0,
            orient="horizontal",
            variable=self.zoom_var,
            command=self.handle_zoom_change,
        )
        self.zoom_slider.grid(row=3, column=1, sticky="ew", pady=2)

        # Optional: Display the zoom value next to the slider
        self.zoom_value_label = ttk.Label(self, text=f"{self.zoom_var.get():.1f}x")
        self.zoom_value_label.grid(row=3, column=2, sticky="w")

        self.columnconfigure(1, weight=1)

    def update_ui(self, status: StreamingStatus) -> None:
        if status in [
            StreamingStatus.IDLE,
            StreamingStatus.DISCONNECTED,
        ]:
            self.camera_combo["state"] = "normal"
            self.resolution_combo["state"] = "normal"
            self.fps_combo["state"] = "normal"
        elif status in [
            StreamingStatus.CONNECTING,
            StreamingStatus.CONNECTED,
            StreamingStatus.DISCONNECTING,
        ]:
            self.camera_combo["state"] = "disabled"
            self.resolution_combo["state"] = "disabled"
            self.fps_combo["state"] = "disabled"
        else:
            self.camera_combo["state"] = "disabled"
            self.resolution_combo["state"] = "disabled"
            self.fps_combo["state"] = "disabled"

    def handle_camera_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Camera changed to: {self.camera_var.get()}")
        self.app_cfg.camera_id = self.camera_combo.current()
        self.app_cfg.save()
        self.reconnect_camera_callback()

    def handle_resolution_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Resolution set to: {self.resolution_var.get()}")
        self.app_cfg.resolution = list(CameraResolution)[self.resolution_combo.current()]
        self.app_cfg.save()
        self.reconnect_camera_callback()

    def handle_fps_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"FPS set to: {self.fps_var.get()}")
        self.app_cfg.fps = int(self.fps_var.get())
        self.app_cfg.save()
        self.reconnect_camera_callback()

    def handle_zoom_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        value = float(self.zoom_var.get())
        self.status_callback(f"Zoom set to: {value:.1f}x")
        self.zoom_value_label.config(text=f"{value:.1f}x")

        # Store zoom in AppData (if property exists)
        if hasattr(self.app_cfg, "zoom"):
            self.app_cfg.zoom = value
            self.app_cfg.save()
