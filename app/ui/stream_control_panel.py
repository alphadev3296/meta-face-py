import asyncio
import threading
from collections.abc import Callable, Coroutine
from tkinter import ttk
from typing import Any


class StreamControlPanel(ttk.LabelFrame):
    """Stream control buttons"""

    def __init__(
        self,
        parent: ttk.Frame,
        status_callback: Callable[[str], None],
        connect_callback: Callable[[], Coroutine[Any, Any, None]],
        disconnect_callback: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        super().__init__(parent, text="Stream Controls", padding=5)
        self.status_callback = status_callback
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback

        # Connect button
        self.connect_btn = ttk.Button(self, text="Connect", command=self.on_connect, width=18)
        self.connect_btn.grid(row=0, column=0, pady=2, sticky="ew")

        # Disconnect button
        self.disconnect_btn = ttk.Button(
            self, text="Disconnect", command=self.on_disconnect, state="disabled", width=18
        )
        self.disconnect_btn.grid(row=1, column=0, pady=2, sticky="ew")

        self.columnconfigure(0, weight=1)

    def on_connect(self) -> None:
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_callback("Connecting to server...")
        threading.Thread(target=lambda: asyncio.run(self.connect_callback()), daemon=True).start()

    def on_disconnect(self) -> None:
        self.disconnect_btn.config(state="disabled")
        self.connect_btn.config(state="normal")
        self.status_callback("Disconnecting from server...")
        threading.Thread(target=lambda: asyncio.run(self.disconnect_callback()), daemon=True).start()
