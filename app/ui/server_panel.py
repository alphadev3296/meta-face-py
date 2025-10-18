import asyncio
import threading
import tkinter as tk
from collections.abc import Callable, Coroutine
from tkinter import ttk
from typing import Any

from loguru import logger

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

        # Create event loop
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()

        # Server address
        ttk.Label(self, text="Address:", width=9, anchor="e").grid(row=0, column=0)
        self.address_var = tk.StringVar(value=self.app_cfg.server_address)
        self.address_entry = ttk.Entry(self, textvariable=self.address_var, width=24)
        self.address_entry.grid(row=0, column=1)
        self.address_entry.bind("<FocusOut>", self.handle_address_change)

        # Secret
        ttk.Label(self, text="Secret:", width=9, anchor="e").grid(row=0, column=2)
        self.secret_var = tk.StringVar(value=self.app_cfg.secret)
        self.secret_entry = ttk.Entry(self, textvariable=self.secret_var, show="*", width=24)
        self.secret_entry.grid(row=0, column=3)
        self.secret_entry.bind("<FocusOut>", self.handle_secret_change)

        # Tasks
        self.connect_task: asyncio.Task[None] | None = None
        self.disconnect_task: asyncio.Task[None] | None = None

        # Connect button
        self.connect_btn = ttk.Button(
            self,
            text="Connect",
            command=self.handle_connect,
            width=18,
        )
        self.connect_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)

        # Disconnect button
        self.disconnect_btn = ttk.Button(
            self,
            text="Disconnect",
            command=self.handle_disconnect,
            state="disabled",
            width=18,
        )
        self.disconnect_btn.grid(row=1, column=2, columnspan=2, sticky="ew", pady=2)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Error in event loop: {e}")
        finally:
            # graceful cleanup
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    def stop_loop(self) -> None:
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop_thread.join()

    def update_ui(self, status: StreamingStatus) -> None:
        if status in [
            StreamingStatus.IDLE,
            StreamingStatus.DISCONNECTED,
        ]:
            self.address_entry["state"] = "normal"
            self.secret_entry["state"] = "normal"
            self.connect_btn["state"] = "normal"
            self.disconnect_btn["state"] = "disabled"
        elif status in [
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
        asyncio.run_coroutine_threadsafe(self.connect_callback(), self.loop)

    def handle_disconnect(self) -> None:
        asyncio.run_coroutine_threadsafe(self.disconnect_callback(), self.loop)
