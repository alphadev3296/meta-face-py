import asyncio
import base64
import tkinter as tk
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
import numpy as np
import pyvirtualcam
from jose import jwt
from loguru import logger

from app.config.auth import config as cfg_auth
from app.network.webrtc import WebRTCClient
from app.schema.app_data import AppConfig, StreamingStatus
from app.schema.camera_resolution import CAMERA_RESOLUTIONS
from app.ui.camera_panel import CameraPanel
from app.ui.processing_panel import ProcessingPanel
from app.ui.server_panel import ServerPanel
from app.ui.status_bar import StatusBar
from app.ui.tone_panel import TonePanel
from app.ui.video_preview import VideoPanel
from app.video.webcam import CvFrame, Webcam


class VideoStreamApp(tk.Tk):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        self.app_data = AppConfig.load()
        self.webcam: Webcam | None = None
        self.webrtc_client: WebRTCClient | None = None
        self.vcam_frames: asyncio.Queue[CvFrame] = asyncio.Queue(maxsize=4)

        self.is_running = True
        self.streaming_status = StreamingStatus.IDLE

        # Configure window
        self.title("Metaface Client")
        self.geometry("920x560")

        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)

        # Create main panels
        self.create_status_bar()
        self.create_control_panel()
        self.create_video_panel()

        # Start background tasks
        self.reconnect_camera()

        self.virtual_camera_task = asyncio.create_task(self.virtual_camera_loop())
        self.camera_task = asyncio.create_task(self.camera_loop())
        self.update_ui_task = asyncio.create_task(self.update_ui_loop())

    async def run_async(self) -> None:
        """
        Run main event loop asynchronously.
        """
        while self.is_running:
            self.update()
            await asyncio.sleep(0.001)

    def destroy(self) -> None:
        """
        Callback method to be called when window is closed
        """
        self.app_data.save()
        self.is_running = False

        super().destroy()

    def create_control_panel(self) -> None:
        """Create left control panel"""
        control_frame = ttk.Frame(self, padding=5)
        control_frame.grid(row=0, column=0, sticky="nsew")

        # Configure control frame grid
        control_frame.columnconfigure(0, weight=0)
        control_frame.columnconfigure(1, weight=0)
        control_frame.columnconfigure(2, weight=0)
        control_frame.columnconfigure(3, weight=0)

        # Add panels
        self.camera_panel = CameraPanel(
            parent=control_frame,
            status_callback=self.update_status_bar,
            app_data=self.app_data,
            reconnect_camera_fn=self.reconnect_camera,
        )
        self.camera_panel.grid(row=0, column=0, sticky="ns", pady=2, padx=2)

        self.processing_panel = ProcessingPanel(
            parent=control_frame,
            status_callback=self.update_status_bar,
            app_cfg=self.app_data,
        )
        self.processing_panel.grid(row=0, column=1, sticky="ns", pady=2, padx=2)

        self.server_panel = ServerPanel(
            parent=control_frame,
            app_cfg=self.app_data,
            status_callback=self.update_status_bar,
            connect_callback=self.connect_server,
            disconnect_callback=self.disconnect_server,
        )
        self.server_panel.grid(row=0, column=2, sticky="ns", pady=2, padx=2)

        self.tone_panel = TonePanel(
            parent=control_frame,
            status_callback=self.update_status_bar,
            app_data=self.app_data,
        )
        self.tone_panel.grid(row=0, column=3, sticky="ns", pady=2, padx=2)

    def create_video_panel(self) -> None:
        """Create right video preview panel"""
        self.video_panel = VideoPanel(self, self.app_data)
        self.video_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def create_status_bar(self) -> None:
        """Create bottom status bar"""
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

    def update_status_bar(self, message: str) -> None:
        """Update status bar message"""
        self.status_bar.set_status(message)

    def reconnect_camera(self) -> None:
        device = self.app_data.camera_id
        if device >= 0:
            width, height = CAMERA_RESOLUTIONS[self.app_data.resolution]
            fps = self.app_data.fps

            if self.webcam is not None:
                self.webcam.close()

            self.webcam = Webcam(
                device=device,
                width=width,
                height=height,
                fps=fps,
                pre_process_callback=self.process_camera_frame,
            )
            self.webcam.open()
        else:
            messagebox.showerror("Error", "No camera device selected")

    def process_camera_frame(self, frame: CvFrame) -> CvFrame:
        # Copy frame
        frame = frame.copy()

        # Zoom frame by center point
        zoom = self.app_data.zoom
        if zoom != 1.0:
            # Resize frame
            old_height, old_width = frame.shape[:2]
            frame = cv2.resize(frame, (int(old_width * zoom), int(old_height * zoom)))

            # Crop by center point
            height, width = frame.shape[:2]
            x = int((width - old_width) / 2)
            y = int((height - old_height) / 2)
            frame = frame[y : y + old_height, x : x + old_width]

        if self.app_data.tone_enabled:
            tonemap_reinhard = cv2.createTonemapReinhard(
                gamma=self.app_data.gamma,
                intensity=self.app_data.intensity,
                light_adapt=self.app_data.light_adapt,
                color_adapt=self.app_data.color_adapt,
            )
            frame_float = frame.astype(np.float32) / 255.0
            result = tonemap_reinhard.process(frame_float)
            frame = np.clip(result * 255, 0, 255).astype(np.uint8)

        return frame

    async def connect_server(self) -> None:
        try:
            self.streaming_status = StreamingStatus.CONNECTING
            self.update_status_bar("Connecting...")

            # Start local camera
            self.reconnect_camera()

            # Create JWT token
            jwt_token = jwt.encode(
                {
                    "sub": "",
                    "exp": datetime.now(tz=UTC) + timedelta(minutes=cfg_auth.JWT_TOKEN_EXPIRE_MINS),
                    "swap_face": self.app_data.swap_face,
                    "enhance_face": self.app_data.enhance_face,
                },
                self.app_data.secret,
                algorithm=cfg_auth.JWT_ALGORITHM,
            )

            # Read photo image
            with Path(self.app_data.photo_path).open("rb") as f:  # noqa: ASYNC230
                photo_data = f.read()
                b64_photo = base64.b64encode(photo_data).decode("utf-8")

            # Create WebRTC client
            if self.webcam is None:
                msg = "Webcam is not initialized"
                raise RuntimeError(msg)  # noqa: TRY301

            self.webrtc_client = WebRTCClient(
                offer_url=f"{self.app_data.server_address}/offer",
                jwt_token=jwt_token,
                b64_photo=b64_photo,
                read_frame_func=self.webcam.read,
                on_recv_frame_callback=self.on_receive_frame,
                on_disconnect_callback=self.disconnect_server,
            )
            await self.webrtc_client.connect()

            self.streaming_status = StreamingStatus.CONNECTED
            self.update_status_bar("Connected")

            await asyncio.sleep(1.0)
            self.update_status_bar("Streaming...")
        except Exception as ex:
            logger.error(f"Failed to connect to server: {ex}")
            await self.disconnect_server()

    async def disconnect_server(self) -> None:
        self.streaming_status = StreamingStatus.DISCONNECTING
        self.update_status_bar("Disconnecting...")

        # Wait for webrtc client to close
        if self.webrtc_client is not None:
            await self.webrtc_client.close()

        # Paint black frame in video panel
        black_frame = np.zeros((360, 640, 3), np.uint8)
        try:
            self.video_panel.show_camera_frame(black_frame)
            self.video_panel.show_processed_frame(black_frame)
        except:  # noqa: E722, S110
            pass

        self.streaming_status = StreamingStatus.DISCONNECTED
        self.update_status_bar("Disconnected")

    def on_receive_frame(self, frame: CvFrame, _frame_number: int) -> None:
        # Show frame
        self.video_panel.show_processed_frame(frame)

        # Put frame in queue
        if self.vcam_frames.full():
            self.vcam_frames.get_nowait()
        self.vcam_frames.put_nowait(frame)

    async def virtual_camera_loop(self) -> None:
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

                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        vcam.send(frame)
                    except Exception as ex:
                        logger.debug(f"Error sending frame to virtual camera: {ex}")
                vcam.close()
            except:  # noqa: E722
                await asyncio.sleep(1.0 / self.app_data.fps)

    async def camera_loop(self) -> None:
        while self.is_running:
            try:
                if self.webcam is not None:
                    frame = self.webcam.read()
                    if frame is not None:
                        self.video_panel.show_camera_frame(frame)
            except Exception as ex:
                logger.debug(f"Error reading frame from camera: {ex}")
            await asyncio.sleep(1.0 / self.app_data.fps)

    async def update_ui_loop(self) -> None:
        prev_state = None
        prev_tone_enabled = None
        while self.is_running:
            try:
                status = self.streaming_status
                tone_enabled = self.app_data.tone_enabled

                if status != prev_state:
                    self.camera_panel.update_ui(status)
                    self.processing_panel.update_ui(status)
                    self.server_panel.update_ui(status)
                    prev_state = status

                if tone_enabled != prev_tone_enabled:
                    self.tone_panel.update_ui(tone_enabled)
                    prev_tone_enabled = tone_enabled

            except Exception as ex:
                logger.debug(f"Error updating UI: {ex}")

            await asyncio.sleep(0.01)
