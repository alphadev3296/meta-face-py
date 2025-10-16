import asyncio

from app.ui.main_window import VideoStreamApp


async def main() -> None:
    app = VideoStreamApp()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
