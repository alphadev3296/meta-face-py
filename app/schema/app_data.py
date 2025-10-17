from enum import StrEnum

from loguru import logger
from pydantic import BaseModel

from app.config.fs import config as cfg_fs
from app.schema.camera_resolution import CameraResolution


class StreamingStatus(StrEnum):
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class AppConfig(BaseModel):
    camera_id: int = -1
    resolution: CameraResolution = CameraResolution.HD
    fps: int = 20
    server_address: str = "http://localhost:8000"
    secret: str = ""
    photo_path: str = ""
    swap_face: bool = True
    enhance_face: bool = True
    show_camera: bool = False
    zoom: float = 1.0

    # Reinhard tonemap settings
    tone_enabled: bool = False
    gamma: float = 1.0
    intensity: float = 0.0
    light_adapt: float = 1.0
    color_adapt: float = 0.0

    # Audio settings
    input_device_idx: int = -1
    output_device_idx: int = -1
    delay_secs: float = 0

    @classmethod
    def load(cls) -> "AppConfig":
        try:
            with cfg_fs.CONF_FILE_PATH.open("r") as f:
                return cls.model_validate_json(f.read())
        except Exception:
            logger.error(f"Failed to load app data from: {cfg_fs.CONF_FILE_PATH}")

        return cls()

    def save(self) -> None:
        try:
            with cfg_fs.CONF_FILE_PATH.open("w") as f:
                f.write(self.model_dump_json(indent=2))
        except Exception:
            logger.error(f"Failed to save app data to: {cfg_fs.CONF_FILE_PATH}")
