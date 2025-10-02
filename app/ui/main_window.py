import tkinter as tk
from tkinter import ttk

from app.schema.app_data import AppData
from app.ui.camera_panel import CameraPanel
from app.ui.local_video_panel import LocalVideoPanel
from app.ui.processing_panel import ProcessingPanel
from app.ui.server_panel import ServerPanel
from app.ui.status_bar import StatusBar
from app.ui.stream_control_panel import StreamControlPanel
from app.ui.video_preview import VideoPreviewPanel


class VideoStreamApp(tk.Tk):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        self.app_data = AppData.load_app_data()

        self.title("Video Streaming Control Panel")
        self.geometry("1200x720")
        self.minsize(1200, 720)

        # Configure grid
        self.columnconfigure(0, weight=0, minsize=220)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Create main panels
        self.create_control_panel()
        self.create_video_panel()
        self.create_status_bar()

    def create_control_panel(self) -> None:
        """Create left control panel"""
        control_frame = ttk.Frame(self, padding=5)
        control_frame.grid(row=0, column=0, sticky="nsew")

        # Configure control frame grid
        control_frame.columnconfigure(0, weight=1)

        # Add panels
        self.camera_panel = CameraPanel(
            parent=control_frame,
            status_callback=self.update_status,
            app_data=self.app_data,
        )
        self.camera_panel.grid(row=0, column=0, sticky="ew", pady=2)

        self.server_panel = ServerPanel(
            parent=control_frame,
            status_callback=self.update_status,
            app_data=self.app_data,
        )
        self.server_panel.grid(row=1, column=0, sticky="ew", pady=2)

        self.processing_panel = ProcessingPanel(
            parent=control_frame,
            status_callback=self.update_status,
            app_data=self.app_data,
        )
        self.processing_panel.grid(row=2, column=0, sticky="ew", pady=2)

        self.local_video_panel = LocalVideoPanel(control_frame, self.update_status)
        self.local_video_panel.grid(row=3, column=0, sticky="nsew", pady=2)
        control_frame.rowconfigure(3, weight=1)

        self.stream_control_panel = StreamControlPanel(control_frame, self.update_status)
        self.stream_control_panel.grid(row=4, column=0, sticky="ew", pady=2)

    def create_video_panel(self) -> None:
        """Create right video preview panel"""
        self.video_panel = VideoPreviewPanel(self)
        self.video_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    def create_status_bar(self) -> None:
        """Create bottom status bar"""
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    def update_status(self, message: str) -> None:
        """Update status bar message"""
        self.status_bar.set_status(message)

    def destroy(self) -> None:
        self.app_data.save_app_data()
        super().destroy()
