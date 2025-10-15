import asyncio
import base64
import tkinter as tk
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tkinter import ttk

import cv2
import numpy as np
import pyvirtualcam
from jose import jwt
from loguru import logger

from app.config.auth import config as cfg_auth
from app.network.webrtc import WebRTCClient
from app.schema.app_data import AppData
from app.schema.camera_resolution import CAMERA_RESOLUTIONS
from app.ui.camera_panel import CameraPanel
from app.ui.local_video_panel import LocalVideoPanel
from app.ui.processing_panel import ProcessingPanel
from app.ui.server_panel import ServerPanel
from app.ui.status_bar import StatusBar
from app.ui.stream_control_panel import StreamControlPanel
from app.ui.video_preview import VideoPreviewPanel
from app.video.webcam import CvFrame, Webcam


class VideoStreamApp(tk.Tk):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        self.app_data = AppData.load_app_data()
        self.webcam: Webcam | None = None
        self.webrtc_client: WebRTCClient | None = None
        self.vcam_frames: asyncio.Queue[CvFrame] = asyncio.Queue(maxsize=10)

        self.is_running = True

        self.title("Video Streaming Control Panel")
        self.geometry("1200x760")
        self.minsize(1200, 760)

        # Configure grid
        self.columnconfigure(0, weight=0, minsize=220)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Create main panels
        self.create_status_bar()
        self.create_control_panel()
        self.create_video_panel()

        # Start virtual camera loop
        asyncio.create_task(self.update_virtual_camera_loop())  # noqa: RUF006

    def create_control_panel(self) -> None:
        """Create left control panel"""
        control_frame = ttk.Frame(self, padding=5)
        control_frame.grid(row=0, column=0, sticky="nsew")

        # Configure control frame grid
        control_frame.columnconfigure(0, weight=1)

        # Add panels
        self.camera_panel = CameraPanel(
            parent=control_frame,
            status_callback=self.update_status,
            app_data=self.app_data,
        )
        self.camera_panel.grid(row=0, column=0, sticky="ew", pady=2)

        self.server_panel = ServerPanel(
            parent=control_frame,
            status_callback=self.update_status,
            app_data=self.app_data,
        )
        self.server_panel.grid(row=1, column=0, sticky="ew", pady=2)

        self.processing_panel = ProcessingPanel(
            parent=control_frame,
            status_callback=self.update_status,
            app_data=self.app_data,
        )
        self.processing_panel.grid(row=2, column=0, sticky="ew", pady=2)

        self.local_video_panel = LocalVideoPanel(
            parent=control_frame,
            status_callback=self.update_status,
            app_data=self.app_data,
        )
        self.local_video_panel.grid(row=3, column=0, sticky="nsew", pady=2)
        control_frame.rowconfigure(3, weight=0)

        self.stream_control_panel = StreamControlPanel(
            parent=control_frame,
            status_callback=self.update_status,
            connect_callback=self.connect_server,
            disconnect_callback=self.disconnect_server,
        )
        self.stream_control_panel.grid(row=4, column=0, sticky="ew", pady=2)

    def create_video_panel(self) -> None:
        """Create right video preview panel"""
        self.video_panel = VideoPreviewPanel(self)
        self.video_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    def create_status_bar(self) -> None:
        """Create bottom status bar"""
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    def update_status(self, message: str) -> None:
        """Update status bar message"""
        self.status_bar.set_status(message)

    def destroy(self) -> None:
        self.app_data.save_app_data()
        asyncio.create_task(self.stop_local_cam())  # noqa: RUF006
        self.is_running = False
        super().destroy()

    async def stop_local_cam(self) -> None:
        if self.webcam is not None:
            self.webcam.close()
            self.webcam = None

        # Wait for webrtc client to close
        if self.webrtc_client is not None:
            await self.webrtc_client.close()

        # Paint black frame
        black_frame = np.zeros((360, 640, 3), np.uint8)
        try:
            self.on_new_frame(black_frame)
            self.on_remote_frame(black_frame, 0)
        except:  # noqa: E722, S110
            pass

    async def connect_server(self) -> None:
        await self.local_cam_thread()

    async def disconnect_server(self) -> None:
        await self.stop_local_cam()

    async def local_cam_thread(self) -> None:
        # Start local camera
        if self.webcam is not None:
            self.webcam.close()

        resolution = CAMERA_RESOLUTIONS[self.app_data.resolution]
        self.webcam = Webcam(
            device=self.app_data.camera_id,
            width=resolution[0],
            height=resolution[1],
            fps=self.app_data.fps,
        )
        self.webcam.open()

        # Create JWT token
        jwt_token = jwt.encode(
            {
                "sub": "",
                "exp": datetime.now(tz=UTC) + timedelta(minutes=cfg_auth.JWT_TOKEN_EXPIRE_MINS),
                "face_swap": self.app_data.face_swap,
                "tone_enhance": False,
                "face_enhance": self.app_data.face_enhance,
            },
            self.app_data.secret,
            algorithm=cfg_auth.JWT_ALGORITHM,
        )

        # Read photo image
        with Path(self.app_data.photo_path).open("rb") as f:  # noqa: ASYNC230
            photo_data = f.read()
            b64_photo = base64.b64encode(photo_data).decode("utf-8")

        # Create WebRTC client
        self.webrtc_client = WebRTCClient(
            offer_url=f"{self.app_data.server_address}/offer",
            jwt_token=jwt_token,
            b64_photo=b64_photo,
            read_frame_func=self.webcam.read,
            on_camera_frame_callback=self.on_new_frame,
            on_recv_frame_callback=self.on_remote_frame,
        )
        await self.webrtc_client.connect()

    async def update_virtual_camera_loop(self) -> None:
        while self.is_running:
            width, height = CAMERA_RESOLUTIONS[self.app_data.resolution]
            fps = self.app_data.fps

            if self.vcam_frames.full():
                self.vcam_frames.get_nowait()
            self.vcam_frames.put_nowait(np.zeros((height, width, 3), np.uint8))

            try:
                vcam = pyvirtualcam.Camera(width, height, fps)
                while self.is_running:
                    new_width, new_height = CAMERA_RESOLUTIONS[self.app_data.resolution]
                    new_fps = self.app_data.fps

                    if width != new_width or height != new_height or fps != new_fps:
                        break

                    try:
                        frame = await self.vcam_frames.get()
                    except:  # noqa: E722
                        # If queue is empty, paint black frame
                        frame = np.zeros((height, width, 3), np.uint8)

                    try:
                        if frame.shape != (height, width, 3):
                            frame = cv2.resize(frame, (width, height))
                        vcam.send(frame)
                    except Exception as ex:
                        logger.debug(f"Error sending frame to virtual camera: {ex}")
                vcam.close()
            except:  # noqa: E722
                asyncio.sleep(0.01)

    def on_new_frame(self, frame: CvFrame) -> None:
        self.local_video_panel.show_frame(frame)

    def on_remote_frame(self, frame: CvFrame, _frame_number: int) -> None:
        # Show frame
        self.video_panel.show_frame(frame)

        # Put frame in queue
        if self.vcam_frames.full():
            self.vcam_frames.get_nowait()
        self.vcam_frames.put_nowait(frame)

    async def run(self) -> None:
        while self.is_running:
            self.update()
            await asyncio.sleep(0.001)
