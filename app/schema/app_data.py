from loguru import logger
from pydantic import BaseModel

from app.config.fs import config as cfg_fs
from app.schema.camera_resolution import CameraResolution


class AppData(BaseModel):
    camera_id: int = 0
    resolution: CameraResolution = CameraResolution.HD
    fps: int = 20
    server_address: str = "http://localhost:8000"
    secret: str = ""
    photo_data: str = ""
    face_swap: bool = True
    face_enhance: bool = True
    show_local_video: bool = False

    @classmethod
    def load_app_data(cls) -> "AppData":
        try:
            with cfg_fs.CONF_FILE_PATH.open("r") as f:
                return cls.model_validate_json(f.read())
        except Exception:
            logger.error(f"Failed to load app data from: {cfg_fs.CONF_FILE_PATH}")

        return cls()

    def save_app_data(self) -> None:
        try:
            with cfg_fs.CONF_FILE_PATH.open("w") as f:
                f.write(self.model_dump_json(indent=2))
        except Exception:
            logger.error(f"Failed to save app data to: {cfg_fs.CONF_FILE_PATH}")
