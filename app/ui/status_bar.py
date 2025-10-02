import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    """Status bar at bottom"""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, relief="sunken", borderwidth=1)

        self.status_label = ttk.Label(self, text="Ready", anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=5, pady=2)

    def set_status(self, message: str) -> None:
        self.status_label.config(text=message)
