from enum import StrEnum


class CameraResolution(StrEnum):
    HD_4 = "HD/4"
    VGA = "VGA"
    HD = "HD"
    FHD = "FHD"


CAMERA_RESOLUTIONS: dict[CameraResolution, tuple[int, int]] = {
    CameraResolution.HD_4: (640, 360),
    CameraResolution.VGA: (640, 480),
    CameraResolution.HD: (1280, 720),
    CameraResolution.FHD: (1920, 1080),
}
