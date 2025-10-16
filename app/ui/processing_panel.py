import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from app.schema.app_data import AppConfig, StreamingStatus


class ProcessingPanel(ttk.LabelFrame):
    """Processing options panel"""

    def __init__(
        self,
        parent: ttk.Frame,
        status_callback: Callable[[str], None],
        app_cfg: AppConfig,
    ) -> None:
        super().__init__(parent, text="Processing", padding=5)

        self.app_cfg = app_cfg
        self.status_callback = status_callback

        # Photo selection
        self.select_btn = ttk.Button(self, text="Select Photo", command=self.select_photo, width=18)
        self.select_btn.grid(row=0, column=0, columnspan=2, pady=2, sticky="ew")

        # Photo preview
        self.preview_frame = ttk.Frame(self, relief="sunken", borderwidth=1, height=120)
        self.preview_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        self.preview_frame.grid_propagate(False)  # noqa: FBT003

        self.preview_label = ttk.Label(self.preview_frame, text="No photo selected", anchor="center")
        self.preview_label.pack(fill="both", expand=True)

        # Swap face checkbox
        self.swapface_var = tk.BooleanVar(value=self.app_cfg.swap_face)
        self.swapface_cb = ttk.Checkbutton(
            self, text="Swap Face", variable=self.swapface_var, command=self.handle_swapface_toggle
        )
        self.swapface_cb.grid(row=2, column=0, sticky="w", pady=2)

        # Enhance face checkbox
        self.enhanceface_var = tk.BooleanVar(value=self.app_cfg.enhance_face)
        self.enhanceface_cb = ttk.Checkbutton(
            self, text="Enhance Face", variable=self.enhanceface_var, command=self.handle_enhanceface_toggle
        )
        self.enhanceface_cb.grid(row=2, column=1, sticky="w", pady=2)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Preview update
        if Path(self.app_cfg.photo_path).is_file():
            self.update_preview(self.app_cfg.photo_path)

    def update_ui(self, status: StreamingStatus) -> None:
        if status in [
            StreamingStatus.IDLE,
            StreamingStatus.DISCONNECTED,
        ]:
            self.select_btn["state"] = "normal"
            self.swapface_cb["state"] = "normal"
            self.enhanceface_cb["state"] = "normal"
        elif status in [
            StreamingStatus.CONNECTING,
            StreamingStatus.CONNECTED,
            StreamingStatus.DISCONNECTING,
        ]:
            self.select_btn["state"] = "disabled"
            self.swapface_cb["state"] = "disabled"
            self.enhanceface_cb["state"] = "disabled"
        else:
            self.select_btn["state"] = "disabled"
            self.swapface_cb["state"] = "disabled"
            self.enhanceface_cb["state"] = "disabled"

    def select_photo(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self.app_cfg.photo_path = filename
            self.app_cfg.save()

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

    def handle_swapface_toggle(self) -> None:
        status = "enabled" if self.swapface_var.get() else "disabled"
        self.status_callback(f"Toggle swap face: {status}")
        self.app_cfg.swap_face = self.swapface_var.get()
        self.app_cfg.save()

    def handle_enhanceface_toggle(self) -> None:
        status = "enabled" if self.enhanceface_var.get() else "disabled"
        self.status_callback(f"Toggle enhance face: {status}")
        self.app_cfg.enhance_face = self.enhanceface_var.get()
        self.app_cfg.save()
