import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from app.schema.app_data import AppData


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

        # Show/hide checkbox
        self.show_var = tk.BooleanVar(value=self.app_data.show_local_video)
        self.show_cb = ttk.Checkbutton(
            self, text="Show Local Video", variable=self.show_var, command=self.on_show_toggle
        )
        self.show_cb.grid(row=0, column=0, sticky="w", pady=2)

        # Video preview
        self.preview_frame = ttk.Frame(self, relief="sunken", borderwidth=1, height=120)
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
