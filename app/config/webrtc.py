from pydantic_settings import BaseSettings


class Config(BaseSettings):
    VCAM_FRAME_QUEUE_SIZE: int = 4
    STATS_QUEUE_SIZE: int = 4

    ROUNT_TRIP_TIME_THRESHOLD: float = 0.01  # seconds
    DELAY_OFFSET: float = 0.3  # seconds


config = Config()
