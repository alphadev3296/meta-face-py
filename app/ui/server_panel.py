import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class ServerPanel(ttk.LabelFrame):
    """Server configuration panel"""

    def __init__(self, parent: ttk.Frame, status_callback: Callable[[str], None]) -> None:
        super().__init__(parent, text="Server", padding=5)
        self.status_callback = status_callback

        # Server address
        ttk.Label(self, text="Address:").grid(row=0, column=0, sticky="w", pady=2)
        self.address_var = tk.StringVar(value="localhost:8080")
        self.address_entry = ttk.Entry(self, textvariable=self.address_var, width=18)
        self.address_entry.grid(row=0, column=1, pady=2, sticky="ew")
        self.address_entry.bind("<FocusOut>", self.on_address_change)

        # Secret
        ttk.Label(self, text="Secret:").grid(row=1, column=0, sticky="w", pady=2)
        self.secret_var = tk.StringVar()
        self.secret_entry = ttk.Entry(self, textvariable=self.secret_var, show="*", width=18)
        self.secret_entry.grid(row=1, column=1, pady=2, sticky="ew")
        self.secret_entry.bind("<FocusOut>", self.on_secret_change)

        self.columnconfigure(1, weight=1)

    def on_address_change(self, _event=None) -> None:  # type: ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Server address updated: {self.address_var.get()}")

    def on_secret_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        if self.secret_var.get():
            self.status_callback("Secret updated")
