from enum import StrEnum


class CameraResolution(StrEnum):
    VGA = "VGA"
    HD = "HD"


CAMERA_RESOLUTIONS: dict[CameraResolution, tuple[int, int]] = {
    CameraResolution.VGA: (640, 480),
    CameraResolution.HD: (1280, 720),
}
