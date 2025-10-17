import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

import sounddevice as sd
from loguru import logger

from app.schema.app_data import AppConfig, StreamingStatus


class AudioPanel(ttk.LabelFrame):
    """Audio configuration panel"""

    def __init__(
        self,
        parent: ttk.Frame,
        app_data: AppConfig,
        status_callback: Callable[[str], None],
        reconnect_audio_fn: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, text="Audio", padding=5)

        self.app_cfg = app_data
        self.status_callback = status_callback
        self.reconnect_audio_callback = reconnect_audio_fn

        # Audio selection
        self.refresh_audio_devices_list_btn = ttk.Button(
            self, text="Refresh", command=self.handle_refresh_audio_devices_list
        )
        self.refresh_audio_devices_list_btn.grid(row=0, column=0, columnspan=2, pady=2, sticky="w")

        self.input_devices = self.list_input_devices()
        self.output_devices = self.list_output_devices()

        current_input_device_name = (
            self.input_devices[self.app_cfg.input_device_idx]
            if len(self.input_devices) > self.app_cfg.input_device_idx
            else ""
        )
        current_output_device_name = (
            self.output_devices[self.app_cfg.output_device_idx]
            if len(self.output_devices) > self.app_cfg.output_device_idx
            else ""
        )

        ttk.Label(self, text="Input Device:").grid(row=1, column=0, sticky="w", pady=2)
        self.input_device_var = tk.StringVar(value=current_input_device_name)
        self.input_device_combo = ttk.Combobox(
            self,
            textvariable=self.input_device_var,
            values=self.input_devices,
            state="readonly",
        )
        self.input_device_combo.grid(row=1, column=1, pady=2, sticky="ew")
        if self.input_devices:
            self.input_device_combo.current(
                min(len(self.input_device_combo["values"]) - 1, max(self.app_cfg.input_device_idx, 0))
            )
        else:
            messagebox.showerror("Error", "No input devices found")
            self.app_cfg.input_device_idx = -1
        self.input_device_combo.bind("<<ComboboxSelected>>", self.handle_input_device_selected)

        ttk.Label(self, text="Output Device:").grid(row=2, column=0, sticky="w", pady=2)
        self.output_device_var = tk.StringVar(value=current_output_device_name)
        self.output_device_combo = ttk.Combobox(
            self,
            textvariable=self.output_device_var,
            values=self.output_devices,
            state="readonly",
        )
        self.output_device_combo.grid(row=2, column=1, pady=2, sticky="ew")
        if self.output_devices:
            self.output_device_combo.current(
                min(len(self.output_device_combo["values"]) - 1, max(self.app_cfg.output_device_idx, 0))
            )
        else:
            messagebox.showerror("Error", "No output devices found")
            self.app_cfg.output_device_idx = -1
        self.output_device_combo.bind("<<ComboboxSelected>>", self.handle_output_device_selected)

    def update_ui(self, status: StreamingStatus) -> None:
        if status in [
            StreamingStatus.IDLE,
            StreamingStatus.DISCONNECTED,
        ]:
            self.refresh_audio_devices_list_btn["state"] = "normal"
            self.input_device_combo["state"] = "readonly"
            self.output_device_combo["state"] = "readonly"
        elif status in [
            StreamingStatus.CONNECTING,
            StreamingStatus.CONNECTED,
            StreamingStatus.DISCONNECTING,
        ]:
            self.refresh_audio_devices_list_btn["state"] = "disabled"
            self.input_device_combo["state"] = "disabled"
            self.output_device_combo["state"] = "disabled"
        else:
            self.refresh_audio_devices_list_btn["state"] = "disabled"
            self.input_device_combo["state"] = "disabled"
            self.output_device_combo["state"] = "disabled"

    def handle_refresh_audio_devices_list(self) -> None:
        input_devices = self.list_input_devices()
        if not input_devices:
            self.status_callback("No input devices found")
            messagebox.showerror("Error", "No input devices found")
            self.app_cfg.input_device_idx = -1
            return

        self.input_device_combo["values"] = input_devices
        self.input_device_combo.current(
            min(len(self.input_device_combo["values"]) - 1, max(self.app_cfg.input_device_idx, 0))
        )
        self.input_device_combo.event_generate("<<ComboboxSelected>>")
        self.status_callback("Input devices list refreshed")

        output_devices = self.list_output_devices()
        if not output_devices:
            self.status_callback("No output devices found")
            messagebox.showerror("Error", "No output devices found")
            self.app_cfg.output_device_idx = -1
            return

        self.output_device_combo["values"] = output_devices
        self.output_device_combo.current(
            min(len(self.output_device_combo["values"]) - 1, max(self.app_cfg.output_device_idx, 0))
        )
        self.output_device_combo.event_generate("<<ComboboxSelected>>")
        self.status_callback("Output devices list refreshed")

    def handle_input_device_selected(self, _event: tk.Event) -> None:
        self.status_callback(f"Input device selected: {self.input_device_var.get()}")
        self.app_cfg.input_device_idx = self.input_device_combo.current()
        self.app_cfg.save()

        if self.reconnect_audio_callback:
            self.reconnect_audio_callback()

    def handle_output_device_selected(self, _event: tk.Event) -> None:
        self.status_callback(f"Output device selected: {self.output_device_var.get()}")
        self.app_cfg.output_device_idx = self.output_device_combo.current()
        self.app_cfg.save()

        if self.reconnect_audio_callback:
            self.reconnect_audio_callback()

    def list_input_devices(self) -> list[str]:
        ret: list[str] = []

        devices = sd.query_devices()
        hostapis = sd.query_hostapis()

        for i, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                host_api_name = hostapis[device["hostapi"]]["name"]
                if host_api_name != "MME":
                    continue

                ret.append(f"{i}. {device['name']}")
        return ret

    def list_output_devices(self) -> list[str]:
        ret: list[str] = []

        devices = sd.query_devices()
        hostapis = sd.query_hostapis()

        for i, device in enumerate(devices):
            if device["max_output_channels"] > 0:
                host_api_name = hostapis[device["hostapi"]]["name"]
                if host_api_name != "MME":
                    continue

                ret.append(f"{i}. {device['name']}")
        return ret

    def get_input_device_id(self) -> int | None:
        try:
            return int(self.input_device_var.get().split(".")[0])
        except Exception as ex:
            logger.error(f"Failed to get input device id: {ex}")
            return None

    def get_output_device_id(self) -> int | None:
        try:
            return int(self.output_device_var.get().split(".")[0])
        except Exception as ex:
            logger.error(f"Failed to get output device id: {ex}")
            return None
