import tkinter as tk
from tkinter import ttk


class VideoPreviewPanel(ttk.LabelFrame):
    """Main video preview panel"""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, text="Camera Preview", padding=5)

        self.preview_label = ttk.Label(
            self, text="Camera Preview", anchor="center", background="gray30", foreground="white"
        )
        self.preview_label.pack(fill="both", expand=True)

        # Placeholder for video feed
        self.cap = None
        self.running = False
