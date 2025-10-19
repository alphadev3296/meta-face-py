import asyncio
import base64
import threading
import time
import tkinter as tk
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

import cv2
import numpy as np
import pyvirtualcam
from aiortc import RTCRemoteInboundRtpStreamStats
from jose import jwt
from loguru import logger

from app.config.auth import config as cfg_auth
from app.media.audio import AudioDelay
from app.media.webcam import CvFrame, Webcam
from app.network.webrtc import WebRTCClient
from app.schema.app_data import AppConfig, StreamingStatus
from app.schema.camera_resolution import CAMERA_RESOLUTIONS
from app.schema.webrtc import WebRTCStats
from app.ui.audio_panel import AudioPanel
from app.ui.camera_panel import CameraPanel
from app.ui.processing_panel import ProcessingPanel
from app.ui.server_panel import ServerPanel
from app.ui.status_bar import StatusBar
from app.ui.tone_panel import TonePanel
from app.ui.video_preview import VideoPanel


class VideoStreamApp(tk.Tk):
    """Main application window"""

    def __init__(self) -> None:
        super().__init__()

        self.app_data = AppConfig.load()
        self.webcam: Webcam | None = None
        self.audio_delay: AudioDelay | None = None
        self.webrtc_client: WebRTCClient | None = None
        self.vcam_frame: CvFrame = np.zeros((480, 640, 3), np.uint8)
        self.vcam_frame_lock = threading.Lock()
        self.stats: WebRTCStats | None = None
        self.stats_lock = threading.Lock()

        self.is_running = True
        self.streaming_status = StreamingStatus.IDLE

        # Configure window
        self.title("Metaface Client")
        self.geometry("950x680")
        self.minsize(950, 680)

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
        self.reconnect_audio_delay()

        self.virtual_camera_thread = threading.Thread(target=self.virtual_camera_loop, daemon=True)
        self.camera_display_thread = threading.Thread(target=self.camera_display_loop, daemon=True)
        self.update_ui_thread = threading.Thread(target=self.update_ui_loop, daemon=True)

        self.virtual_camera_thread.start()
        self.camera_display_thread.start()
        self.update_ui_thread.start()

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

        self.audio_panel = AudioPanel(
            parent=control_frame,
            status_callback=self.update_status_bar,
            app_data=self.app_data,
            reconnect_audio_fn=self.reconnect_audio_delay,
        )
        self.audio_panel.grid(row=0, column=1, sticky="ns", pady=2, padx=2)

        self.processing_panel = ProcessingPanel(
            parent=control_frame,
            status_callback=self.update_status_bar,
            app_cfg=self.app_data,
        )
        self.processing_panel.grid(row=0, column=2, sticky="ns", pady=2, padx=2)

        self.tone_panel = TonePanel(
            parent=control_frame,
            status_callback=self.update_status_bar,
            app_data=self.app_data,
        )
        self.tone_panel.grid(row=0, column=3, sticky="ns", pady=2, padx=2)

        self.server_panel = ServerPanel(
            parent=control_frame,
            app_cfg=self.app_data,
            status_callback=self.update_status_bar,
            connect_callback=self.connect_server,
            disconnect_callback=self.disconnect_server,
        )
        self.server_panel.grid(row=1, column=0, columnspan=3, sticky="w", pady=2, padx=2)

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

    def reconnect_audio_delay(self) -> None:
        input_device_id = self.audio_panel.get_input_device_id()
        output_device_id = self.audio_panel.get_output_device_id()
        if input_device_id is not None and output_device_id is not None:
            if self.audio_delay is not None:
                self.audio_delay.close()

            self.audio_delay = AudioDelay(
                input_device_id=input_device_id,
                output_device_id=output_device_id,
                delay_secs=self.app_data.delay_secs,
            )
            self.audio_delay.open()
        else:
            messagebox.showerror("Error", "No audio device selected")

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
            if self.streaming_status not in [StreamingStatus.IDLE, StreamingStatus.DISCONNECTED]:
                return

            self.streaming_status = StreamingStatus.CONNECTING
            self.update_status_bar("Connecting...")

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
            self.streaming_status = StreamingStatus.DISCONNECTED
            self.update_status_bar("Disconnected")

    async def disconnect_server(self) -> None:
        if self.streaming_status is not StreamingStatus.CONNECTED:
            return

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

    async def on_receive_frame(self, frame: CvFrame, _frame_number: int) -> None:
        try:
            # Show frame
            self.video_panel.show_processed_frame(frame)

            # Store frame
            with self.vcam_frame_lock:
                self.vcam_frame = frame

            # Put stats in queue
            if self.webrtc_client is None:
                logger.warning("WebRTC client is not initialized")
                return

            webrtc_stats: dict[str, Any] = await self.webrtc_client.pc.getStats()
            for field in webrtc_stats.values():
                if isinstance(field, RTCRemoteInboundRtpStreamStats):
                    with self.stats_lock:
                        self.stats = WebRTCStats(
                            round_trip_time=field.roundTripTime or 0,
                        )

        except Exception as ex:
            logger.error(f"Failed to receive frame: {ex}")

    def virtual_camera_loop(self) -> None:
        while self.is_running:
            width, height = CAMERA_RESOLUTIONS[self.app_data.resolution]
            fps = self.app_data.fps

            with self.vcam_frame_lock:
                self.vcam_frame = np.zeros((height, width, 3), np.uint8)

            try:
                vcam = pyvirtualcam.Camera(width, height, fps)
                while self.is_running:
                    new_width, new_height = CAMERA_RESOLUTIONS[self.app_data.resolution]
                    new_fps = self.app_data.fps

                    if width != new_width or height != new_height or fps != new_fps:
                        break

                    frame = np.zeros((height, width, 3), np.uint8)
                    with self.vcam_frame_lock:
                        frame = self.vcam_frame

                    try:
                        if frame.shape != (height, width, 3):
                            frame = cv2.resize(frame, (width, height))  # type: ignore  # noqa: PGH003

                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # type: ignore # noqa: PGH003
                        vcam.send(frame)
                    except Exception as ex:
                        logger.debug(f"Error sending frame to virtual camera: {ex}")
                    time.sleep(1.0 / self.app_data.fps)
                vcam.close()
            except Exception as ex:
                time.sleep(1.0 / self.app_data.fps)
                logger.debug(f"Error creating virtual camera: {ex}")

    def camera_display_loop(self) -> None:
        while self.is_running:
            if self.webcam is not None:
                self.video_panel.show_camera_frame(self.webcam.read())
            time.sleep(1.0 / self.app_data.fps)

    def update_ui_loop(self) -> None:
        prev_state = None
        prev_tone_enabled = None
        while self.is_running:
            try:
                status = self.streaming_status
                tone_enabled = self.app_data.tone_enabled

                if status != prev_state:
                    self.camera_panel.update_ui(status)
                    self.audio_panel.update_ui(status)
                    self.processing_panel.update_ui(status)
                    self.server_panel.update_ui(status)
                    prev_state = status

                if tone_enabled != prev_tone_enabled:
                    self.tone_panel.update_ui(tone_enabled)
                    prev_tone_enabled = tone_enabled

            except Exception as ex:
                logger.debug(f"Error updating UI: {ex}")

            time.sleep(0.01)
