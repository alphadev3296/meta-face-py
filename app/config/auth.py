from pydantic_settings import BaseSettings


class Config(BaseSettings):
    JWT_ALGORITHM: str = "HS256"
    JWT_TOKEN_EXPIRE_MINS: int = 5


config = Config()
