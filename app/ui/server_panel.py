import asyncio
import tkinter as tk
from collections.abc import Callable, Coroutine
from tkinter import ttk
from typing import Any

from app.schema.app_data import AppConfig, StreamingStatus


class ServerPanel(ttk.LabelFrame):
    """Server configuration panel"""

    def __init__(
        self,
        parent: ttk.Frame,
        app_cfg: AppConfig,
        status_callback: Callable[[str], None],
        connect_callback: Callable[[], Coroutine[Any, Any, None]],
        disconnect_callback: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        super().__init__(parent, text="Server", padding=5)

        self.app_cfg = app_cfg

        # Callbacks
        self.status_callback = status_callback
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback

        # Server address
        ttk.Label(self, text="Address:").grid(row=0, column=0, sticky="w", pady=2)
        self.address_var = tk.StringVar(value=self.app_cfg.server_address)
        self.address_entry = ttk.Entry(self, textvariable=self.address_var, width=18)
        self.address_entry.grid(row=0, column=1, pady=2, sticky="ew")
        self.address_entry.bind("<FocusOut>", self.handle_address_change)

        # Secret
        ttk.Label(self, text="Secret:").grid(row=1, column=0, sticky="w", pady=2)
        self.secret_var = tk.StringVar(value=self.app_cfg.secret)
        self.secret_entry = ttk.Entry(self, textvariable=self.secret_var, show="*", width=18)
        self.secret_entry.grid(row=1, column=1, pady=2, sticky="ew")
        self.secret_entry.bind("<FocusOut>", self.handle_secret_change)

        # Tasks
        self.connect_task: asyncio.Task[None] | None = None
        self.disconnect_task: asyncio.Task[None] | None = None

        # Connect button
        self.connect_btn = ttk.Button(self, text="Connect", command=self.handle_connect, width=18)
        self.connect_btn.grid(row=2, column=0, columnspan=2, pady=2, sticky="ew")

        # Disconnect button
        self.disconnect_btn = ttk.Button(
            self, text="Disconnect", command=self.hadle_disconnect, state="disabled", width=18
        )
        self.disconnect_btn.grid(row=3, column=0, columnspan=2, pady=2, sticky="ew")

        self.columnconfigure(0, weight=1)

    def update_ui(self, streaming_status: StreamingStatus) -> None:
        if streaming_status in [
            StreamingStatus.IDLE,
            StreamingStatus.DISCONNECTED,
        ]:
            self.address_entry["state"] = "normal"
            self.secret_entry["state"] = "normal"
            self.connect_btn["state"] = "normal"
            self.disconnect_btn["state"] = "disabled"
        elif streaming_status in [
            StreamingStatus.CONNECTING,
            StreamingStatus.CONNECTED,
            StreamingStatus.DISCONNECTING,
        ]:
            self.address_entry["state"] = "disabled"
            self.secret_entry["state"] = "disabled"
            self.connect_btn["state"] = "disabled"
            self.disconnect_btn["state"] = "normal"
        else:
            self.address_entry["state"] = "disabled"
            self.secret_entry["state"] = "disabled"
            self.connect_btn["state"] = "disabled"
            self.disconnect_btn["state"] = "disabled"

    def handle_address_change(self, _event=None) -> None:  # type: ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Server address updated: {self.address_var.get()}")
        self.app_cfg.server_address = self.address_var.get()

    def handle_secret_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        if self.secret_var.get():
            self.status_callback("Secret updated")
            self.app_cfg.secret = self.secret_var.get()
            self.app_cfg.save()

    def handle_connect(self) -> None:
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_callback("Connecting to server...")
        self.connect_task = asyncio.create_task(self.connect_callback())

    def hadle_disconnect(self) -> None:
        self.disconnect_btn.config(state="disabled")
        self.connect_btn.config(state="normal")
        self.status_callback("Disconnecting from server...")
        self.disconnect_task = asyncio.create_task(self.disconnect_callback())
