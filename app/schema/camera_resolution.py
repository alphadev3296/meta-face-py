from enum import StrEnum


class CameraResolution(StrEnum):
    VGA = "VGA"
    HD = "HD"
    FHD = "FHD"


CAMERA_RESOLUTIONS: dict[CameraResolution, tuple[int, int]] = {
    CameraResolution.VGA: (640, 480),
    CameraResolution.HD: (1280, 720),
    CameraResolution.FHD: (1920, 1080),
}
