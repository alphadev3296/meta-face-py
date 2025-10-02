from pathlib import Path


class Config:
    ROOT_DIR: Path = Path(__file__).parent.parent.parent
    CONF_FILE_PATH: Path = ROOT_DIR / "conf.json"


config = Config()
