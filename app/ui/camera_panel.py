import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from app.media.webcam import Webcam
from app.schema.app_data import AppConfig, StreamingStatus
from app.schema.camera_resolution import CAMERA_RESOLUTIONS, CameraResolution


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
        self.refrech_camera_list_btn = ttk.Button(self, text="Refresh", command=self.handle_refresh_camera_list)
        self.refrech_camera_list_btn.grid(row=0, column=0, columnspan=2, pady=2, sticky="w")

        devices = Webcam.list_webcams()
        ttk.Label(self, text="Camera:").grid(row=1, column=0, sticky="w", pady=2)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(
            self,
            textvariable=self.camera_var,
            values=[f"{dev[1]}" for dev in devices],
            state="readonly",
        )
        self.camera_combo.grid(row=1, column=1, pady=2, sticky="ew")
        if devices:
            self.camera_combo.current(min(len(self.camera_combo["values"]) - 1, max(self.app_cfg.camera_id, 0)))
        else:
            messagebox.showerror("Error", "No cameras found")
            self.app_cfg.camera_id = -1
        self.camera_combo.bind("<<ComboboxSelected>>", self.handle_camera_change)

        # Resolution selection
        ttk.Label(self, text="Resolution:").grid(row=2, column=0, sticky="w", pady=2)
        self.resolution_var = tk.StringVar()
        self.resolution_combo = ttk.Combobox(
            self,
            textvariable=self.resolution_var,
            values=[
                f"{cr.value} ({CAMERA_RESOLUTIONS[cr][0]}x{CAMERA_RESOLUTIONS[cr][1]})" for cr in list(CameraResolution)
            ],
            state="readonly",
        )
        self.resolution_combo.grid(row=2, column=1, pady=2, sticky="ew")
        self.resolution_combo.current(list(CameraResolution).index(self.app_cfg.resolution))
        self.resolution_combo.bind("<<ComboboxSelected>>", self.handle_resolution_change)

        # FPS selection
        ttk.Label(self, text="FPS:").grid(row=3, column=0, sticky="w", pady=2)
        self.fps_var = tk.StringVar()
        self.fps_combo = ttk.Combobox(
            self,
            textvariable=self.fps_var,
            values=["5", "10", "15", "20", "30"],
            state="readonly",
        )
        self.fps_combo.grid(row=3, column=1, pady=2, sticky="ew")
        self.fps_combo.set(str(self.app_cfg.fps))
        self.fps_combo.bind("<<ComboboxSelected>>", self.handle_fps_change)

        # Zoom slider
        ttk.Label(self, text="Zoom:").grid(row=4, column=0, sticky="w", pady=2)
        self.zoom_var = tk.DoubleVar(value=self.app_cfg.zoom)
        self.zoom_slider = ttk.Scale(
            self,
            from_=1.0,
            to=4.0,
            orient="horizontal",
            variable=self.zoom_var,
            command=self.handle_zoom_change,
        )
        self.zoom_slider.grid(row=4, column=1, sticky="ew", pady=2)

        self.zoom_value_label = ttk.Label(self, text=f"{self.zoom_var.get():.1f}x")
        self.zoom_value_label.grid(row=4, column=2, sticky="w")

        self.columnconfigure(1, weight=1)

    def update_ui(self, status: StreamingStatus) -> None:
        if status in [
            StreamingStatus.IDLE,
            StreamingStatus.DISCONNECTED,
        ]:
            self.refrech_camera_list_btn["state"] = "normal"
            self.camera_combo["state"] = "readonly"
            self.resolution_combo["state"] = "readonly"
            self.fps_combo["state"] = "readonly"
        elif status in [
            StreamingStatus.CONNECTING,
            StreamingStatus.CONNECTED,
            StreamingStatus.DISCONNECTING,
        ]:
            self.refrech_camera_list_btn["state"] = "disabled"
            self.camera_combo["state"] = "disabled"
            self.resolution_combo["state"] = "disabled"
            self.fps_combo["state"] = "disabled"
        else:
            self.refrech_camera_list_btn["state"] = "disabled"
            self.camera_combo["state"] = "disabled"
            self.resolution_combo["state"] = "disabled"
            self.fps_combo["state"] = "disabled"

    def handle_refresh_camera_list(self) -> None:
        devices = Webcam.list_webcams()
        if not devices:
            self.status_callback("No cameras found")
            messagebox.showerror("Error", "No cameras found")
            self.app_cfg.camera_id = -1
            return

        self.camera_combo["values"] = [f"{dev[1]}" for dev in devices]
        self.camera_combo.current(min(len(self.camera_combo["values"]) - 1, self.app_cfg.camera_id))
        self.camera_combo.event_generate("<<ComboboxSelected>>")
        self.status_callback("Camera list refreshed")

    def handle_camera_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Camera changed to: {self.camera_var.get()}")
        self.app_cfg.camera_id = self.camera_combo.current()
        self.app_cfg.save()
        self.reconnect_camera_callback()

    def handle_resolution_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Resolution set to {self.resolution_var.get()}")
        self.app_cfg.resolution = list(CameraResolution)[self.resolution_combo.current()]
        self.app_cfg.save()
        self.reconnect_camera_callback()

    def handle_fps_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"FPS set to {self.fps_var.get()}")
        self.app_cfg.fps = int(self.fps_var.get())
        self.app_cfg.save()
        self.reconnect_camera_callback()

    def handle_zoom_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        value = float(self.zoom_var.get())
        self.status_callback(f"Zoom set to {value:.1f}x")
        self.zoom_value_label.config(text=f"{value:.1f}x")

        self.app_cfg.zoom = value
        self.app_cfg.save()
