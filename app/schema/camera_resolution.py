from enum import StrEnum


class CameraResolution(StrEnum):
    VGA = "VGA"
    HD_2 = "HD/2"
    HD = "HD"
    FHD = "FHD"


CAMERA_RESOLUTIONS: dict[CameraResolution, tuple[int, int]] = {
    CameraResolution.VGA: (640, 480),
    CameraResolution.HD_2: (960, 540),
    CameraResolution.HD: (1280, 720),
    CameraResolution.FHD: (1920, 1080),
}
