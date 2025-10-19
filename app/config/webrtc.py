from pydantic_settings import BaseSettings


class Config(BaseSettings):
    VCAM_FRAME_QUEUE_SIZE: int = 4
    STATS_QUEUE_SIZE: int = 4

    ROUNT_TRIP_TIME_THRESHOLD: float = 0.03  # seconds

    HTTP_REQUEST_TIMEOUT: int = 10  # seconds


config = Config()
