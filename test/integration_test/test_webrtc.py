import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
from jose import jwt
from loguru import logger

from app.config.auth import config as cfg_auth
from app.media.webcam import CvFrame, Webcam
from app.network.webrtc import WebRTCClient


async def test_webrtc() -> None:
    # Configuration
    server_url = "http://localhost:8000"
    device_id = 1
    width = 640  # Video width in pixels
    height = 480  # Video height in pixels
    fps = 30  # Frames per second

    webcam = Webcam(
        device=device_id,
        width=width,
        height=height,
        fps=fps,
    )
    webcam.open()

    logger.info("Starting WebRTC client:")
    logger.info(f"  Resolution: {width}x{height}")
    logger.info(f"  FPS: {fps}")

    try:
        # Read photo image
        with Path(r"C:\Users\alpha\Downloads\output.png").open("rb") as f:  # noqa: ASYNC230
            photo_data = base64.b64encode(f.read()).decode("utf-8")

        jwt_token = jwt.encode(
            {
                "sub": "",
                "exp": datetime.now(tz=UTC) + timedelta(minutes=cfg_auth.JWT_TOKEN_EXPIRE_MINS),
                "swap_face": False,
                "enhance_face": False,
            },
            "qC7kQqEnscXo4A3Zh1p6uK2zBdRno8cYPm5t7UHs",
            algorithm=cfg_auth.JWT_ALGORITHM,
        )

        async def recv_frame(frame: CvFrame, pts: int) -> None:
            logger.debug(f"Received frame {pts}: {frame.shape}")

        client = WebRTCClient(
            offer_url=f"{server_url}/offer",
            jwt_token=jwt_token,
            b64_photo=photo_data,
            read_frame_func=webcam.read,
            on_recv_frame_callback=recv_frame,
        )

        await client.connect()

        # Start display loop
        cv2.namedWindow("Processed Stream", cv2.WINDOW_NORMAL)
        while True:
            try:
                # Get frame from queue with timeout
                frame = await client.get_remote_frame(timeout=1.0)

                cv2.imshow("Processed Stream", frame)

                # Break on 'q' key
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            except TimeoutError:
                # No frame available, check for key press
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            except Exception as e:
                logger.error(f"Display error: {e}")
                break
        cv2.destroyAllWindows()
    except KeyboardInterrupt:
        logger.debug("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.close()
