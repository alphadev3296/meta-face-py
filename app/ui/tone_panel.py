import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from app.schema.app_data import AppConfig


class TonePanel(ttk.LabelFrame):
    """Tone configuration panel"""

    def __init__(
        self,
        parent: ttk.Frame,
        status_callback: Callable[[str], None],
        app_data: AppConfig,
    ) -> None:
        super().__init__(parent, text="Tone Adjustment", padding=5)

        self.app_cfg = app_data
        self.status_callback = status_callback

        # Tone check box
        self.tone_check_var = tk.BooleanVar(value=self.app_cfg.tone_enabled)
        self.tone_check = ttk.Checkbutton(
            self,
            text="Enable",
            variable=self.tone_check_var,
            command=self.handle_tone_change,
        )
        self.tone_check.grid(row=4, column=0, sticky="w", pady=2)

        # Gamma slider
        ttk.Label(self, text="Gamma:").grid(row=5, column=0, sticky="w", pady=2)
        self.gamma_var = tk.DoubleVar(value=self.app_cfg.gamma)
        self.gamma_slider = ttk.Scale(
            self,
            from_=1.0,
            to=4.0,
            orient="horizontal",
            variable=self.gamma_var,
            command=self.handle_gamma_change,
        )
        self.gamma_slider.grid(row=5, column=1, sticky="ew", pady=2)

        self.gamma_value_label = ttk.Label(self, text=f"{self.gamma_var.get():.1f}")
        self.gamma_value_label.grid(row=5, column=2, sticky="w")

        # Intensity slider
        ttk.Label(self, text="Intensity:").grid(row=6, column=0, sticky="w", pady=2)
        self.intensity_var = tk.DoubleVar(value=self.app_cfg.intensity)
        self.intensity_slider = ttk.Scale(
            self,
            from_=1.0,
            to=4.0,
            orient="horizontal",
            variable=self.intensity_var,
            command=self.handle_intensity_change,
        )
        self.intensity_slider.grid(row=6, column=1, sticky="ew", pady=2)

        self.intensity_value_label = ttk.Label(self, text=f"{self.intensity_var.get():.1f}")
        self.intensity_value_label.grid(row=6, column=2, sticky="w")

        # Light adapt slider
        ttk.Label(self, text="Light adapt:").grid(row=7, column=0, sticky="w", pady=2)
        self.light_adapt_var = tk.DoubleVar(value=self.app_cfg.light_adapt)
        self.light_adapt_slider = ttk.Scale(
            self,
            from_=1.0,
            to=4.0,
            orient="horizontal",
            variable=self.light_adapt_var,
            command=self.handle_light_adapt_change,
        )
        self.light_adapt_slider.grid(row=7, column=1, sticky="ew", pady=2)

        self.light_adapt_value_label = ttk.Label(self, text=f"{self.light_adapt_var.get():.1f}")
        self.light_adapt_value_label.grid(row=7, column=2, sticky="w")

        # Color adapt slider
        ttk.Label(self, text="Color adapt:").grid(row=8, column=0, sticky="w", pady=2)
        self.color_adapt_var = tk.DoubleVar(value=self.app_cfg.color_adapt)
        self.color_adapt_slider = ttk.Scale(
            self,
            from_=1.0,
            to=4.0,
            orient="horizontal",
            variable=self.color_adapt_var,
            command=self.handle_color_adapt_change,
        )
        self.color_adapt_slider.grid(row=8, column=1, sticky="ew", pady=2)

        self.color_adapt_value_label = ttk.Label(self, text=f"{self.color_adapt_var.get():.1f}")
        self.color_adapt_value_label.grid(row=8, column=2, sticky="w")

        self.columnconfigure(1, weight=1)

    def update_ui(self, tone_enabled: bool) -> None:  # noqa: FBT001
        if tone_enabled:
            self.gamma_slider["state"] = "normal"
            self.intensity_slider["state"] = "normal"
            self.light_adapt_slider["state"] = "normal"
            self.color_adapt_slider["state"] = "normal"
        else:
            self.gamma_slider["state"] = "disabled"
            self.intensity_slider["state"] = "disabled"
            self.light_adapt_slider["state"] = "disabled"
            self.color_adapt_slider["state"] = "disabled"

    def handle_tone_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        self.status_callback(f"Tone set to {self.tone_check_var.get()}")
        self.app_cfg.tone_enabled = self.tone_check_var.get()
        self.app_cfg.save()

    def handle_gamma_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        value = float(self.gamma_var.get())
        self.status_callback(f"Gamma set to {value:.1f}")
        self.gamma_value_label.config(text=f"{value:.1f}")

        self.app_cfg.gamma = value
        self.app_cfg.save()

    def handle_intensity_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        value = float(self.intensity_var.get())
        self.status_callback(f"Intensity set to {value:.1f}")
        self.intensity_value_label.config(text=f"{value:.1f}")

        self.app_cfg.intensity = value
        self.app_cfg.save()

    def handle_light_adapt_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        value = float(self.light_adapt_var.get())
        self.status_callback(f"Light adapt set to {value:.1f}")
        self.light_adapt_value_label.config(text=f"{value:.1f}")

        self.app_cfg.light_adapt = value
        self.app_cfg.save()

    def handle_color_adapt_change(self, _event=None) -> None:  # type:ignore  # noqa: ANN001, PGH003
        value = float(self.color_adapt_var.get())
        self.status_callback(f"Color adapt set to {value:.1f}")
        self.color_adapt_value_label.config(text=f"{value:.1f}")

        self.app_cfg.color_adapt = value
        self.app_cfg.save()
