import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk

from PIL import Image, ImageTk


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
