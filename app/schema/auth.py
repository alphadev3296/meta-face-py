from pydantic import BaseModel


class TokenData(BaseModel):
    sub: str
    exp: int
    face_swap: bool
    face_enhance: bool
