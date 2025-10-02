import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk

from PIL import Image, ImageTk


class CameraPanel(ttk.LabelFrame):
    """Camera configuration panel"""

    def __init__(self, parent: ttk.Frame, status_callback: Callable[[str], None]) -> None:
        super().__init__(parent, text="Camera", padding=5)
        self.status_callback = status_callback

        # Camera selection
        ttk.Label(self, text="Camera:").grid(row=0, column=0, sticky="w", pady=2)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(
            self, textvariable=self.camera_var, values=["Camera 0", "Camera 1", "Camera 2"], state="readonly", width=15
        )
        self.camera_combo.grid(row=0, column=1, pady=2, sticky="ew")
        self.camera_combo.current(0)
        self.camera_combo.bind("<<ComboboxSelected>>", self.on_camera_change)

        # Resolution selection
        ttk.Label(self, text="Resolution:").grid(row=1, column=0, sticky="w", pady=2)
        self.resolution_var = tk.StringVar()
        self.resolution_combo = ttk.Combobox(
            self,
            textvariable=self.resolution_var,
            values=["VGA (640x480)", "HD/2 (960x540)", "HD (1280x720)", "FHD (1920x1080)"],
            state="readonly",
            width=15,
        )
        self.resolution_combo.grid(row=1, column=1, pady=2, sticky="ew")
        self.resolution_combo.current(0)
        self.resolution_combo.bind("<<ComboboxSelected>>", self.on_resolution_change)

        # FPS selection
        ttk.Label(self, text="FPS:").grid(row=2, column=0, sticky="w", pady=2)
        self.fps_var = tk.StringVar()
        self.fps_combo = ttk.Combobox(
            self, textvariable=self.fps_var, values=["5", "10", "25"], state="readonly", width=15
        )
        self.fps_combo.grid(row=2, column=1, pady=2, sticky="ew")
        self.fps_combo.current(2)
        self.fps_combo.bind("<<ComboboxSelected>>", self.on_fps_change)

        self.columnconfigure(1, weight=1)

    def on_camera_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Camera changed to: {self.camera_var.get()}")

    def on_resolution_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Resolution set to: {self.resolution_var.get()}")

    def on_fps_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"FPS set to: {self.fps_var.get()}")


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


class ProcessingPanel(ttk.LabelFrame):
    """Processing options panel"""

    def __init__(self, parent: ttk.Frame, status_callback: Callable[[str], None]) -> None:
        super().__init__(parent, text="Processing", padding=5)
        self.status_callback = status_callback
        self.photo_path: str | None = None

        # Photo selection
        self.select_btn = ttk.Button(self, text="Select Photo", command=self.select_photo, width=18)
        self.select_btn.grid(row=0, column=0, columnspan=2, pady=2, sticky="ew")

        # Photo preview
        self.preview_frame = ttk.Frame(self, relief="sunken", borderwidth=1, height=120)
        self.preview_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        self.preview_frame.grid_propagate(False)  # noqa: FBT003

        self.preview_label = ttk.Label(self.preview_frame, text="No photo selected", anchor="center")
        self.preview_label.pack(fill="both", expand=True)

        # FaceSwap checkbox
        self.faceswap_var = tk.BooleanVar()
        self.faceswap_cb = ttk.Checkbutton(
            self, text="FaceSwap", variable=self.faceswap_var, command=self.on_faceswap_toggle
        )
        self.faceswap_cb.grid(row=2, column=0, sticky="w", pady=2)

        # FaceEnhance checkbox
        self.faceenhance_var = tk.BooleanVar()
        self.faceenhance_cb = ttk.Checkbutton(
            self, text="FaceEnhance", variable=self.faceenhance_var, command=self.on_faceenhance_toggle
        )
        self.faceenhance_cb.grid(row=2, column=1, sticky="w", pady=2)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def select_photo(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self.photo_path = filename
            self.update_preview(filename)
            self.status_callback(f"Photo selected: {filename.split('/')[-1]}")

    def update_preview(self, path: str) -> None:
        if Image is None or ImageTk is None:
            self.preview_label.config(text=f"Preview: {path.split('/')[-1]}\n(PIL not installed)")
            self.status_callback("Photo selected (preview requires PIL)")
            return

        try:
            img = Image.open(path)
            img.thumbnail((150, 120))
            photo = ImageTk.PhotoImage(img)
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo  # type: ignore  # noqa: PGH003
        except Exception as e:
            self.preview_label.config(text=f"Error: {str(e)[:30]}")
            self.status_callback(f"Error loading preview: {e}")

    def on_faceswap_toggle(self) -> None:
        status = "enabled" if self.faceswap_var.get() else "disabled"
        self.status_callback(f"FaceSwap {status}")

    def on_faceenhance_toggle(self) -> None:
        status = "enabled" if self.faceenhance_var.get() else "disabled"
        self.status_callback(f"FaceEnhance {status}")


class LocalVideoPanel(ttk.LabelFrame):
    """Local video preview panel"""

    def __init__(self, parent: ttk.Frame, status_callback: Callable[[str], None]) -> None:
        super().__init__(parent, text="Local Video", padding=5)
        self.status_callback = status_callback

        # Show/hide checkbox
        self.show_var = tk.BooleanVar(value=True)
        self.show_cb = ttk.Checkbutton(
            self, text="Show Local Video", variable=self.show_var, command=self.on_show_toggle
        )
        self.show_cb.grid(row=0, column=0, sticky="w", pady=2)

        # Video preview
        self.preview_frame = ttk.Frame(self, relief="sunken", borderwidth=1, height=1200)
        self.preview_frame.grid(row=1, column=0, pady=5, sticky="ew")

        self.preview_label = ttk.Label(
            self.preview_frame, text="Local Preview", anchor="center", background="gray20", foreground="white"
        )
        self.preview_label.pack(fill="both", expand=True)

        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

    def on_show_toggle(self) -> None:
        if self.show_var.get():
            self.preview_label.pack(fill="both", expand=True)
            self.status_callback("Local video preview shown")
        else:
            self.preview_label.pack_forget()
            self.status_callback("Local video preview hidden")


class StreamControlPanel(ttk.LabelFrame):
    """Stream control buttons"""

    def __init__(self, parent: ttk.Frame, status_callback: Callable[[str], None]) -> None:
        super().__init__(parent, text="Stream Controls", padding=5)
        self.status_callback = status_callback
        self.connected = False

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
        self.connected = True
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_callback("Connecting to server...")
        # Simulate connection
        self.after(1000, lambda: self.status_callback("Connected to server"))

    def on_disconnect(self) -> None:
        self.connected = False
        self.disconnect_btn.config(state="disabled")
        self.connect_btn.config(state="normal")
        self.status_callback("Disconnected from server")


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


class StatusBar(ttk.Frame):
    """Status bar at bottom"""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, relief="sunken", borderwidth=1)

        self.status_label = ttk.Label(self, text="Ready", anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=5, pady=2)

    def set_status(self, message: str) -> None:
        self.status_label.config(text=message)


class VideoStreamApp(tk.Tk):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

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
        self.camera_panel = CameraPanel(control_frame, self.update_status)
        self.camera_panel.grid(row=0, column=0, sticky="ew", pady=2)

        self.server_panel = ServerPanel(control_frame, self.update_status)
        self.server_panel.grid(row=1, column=0, sticky="ew", pady=2)

        self.processing_panel = ProcessingPanel(control_frame, self.update_status)
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


if __name__ == "__main__":
    app = VideoStreamApp()
    app.mainloop()
