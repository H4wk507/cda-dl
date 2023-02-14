import os
import asyncio
import argparse
from aiohttp import ClientSession
from webdriver_manager.chrome import ChromeDriverManager
from cda_downloader.utils import is_video, is_folder, clear
from cda_downloader.video import Video
from cda_downloader.folder import Folder


class Downloader:
    urls: list[str]
    directory: str
    resolution: str
    headers: dict[str, str]
    list_resolutions: bool
    driver_path: str

    def __init__(self, args: argparse.Namespace) -> None:
        self.urls = [url.strip() for url in args.urls]
        self.directory = os.path.abspath(
            os.path.expanduser(os.path.expandvars(args.directory))
        )
        self.resolution = args.resolution
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        self.list_resolutions = args.list_resolutions
        self.driver_path = ""
        asyncio.run(self.main())

    async def main(self) -> None:
        await self.handle_flags()
        self.driver_path = await self.install_and_get_driver_path()
        self.video_urls, self.folder_urls = self.get_urls()
        await self.download_folders()
        await self.download_videos()
        clear()
        print("Skończono pobieranie wszystkich plików.")

    async def handle_flags(self) -> None:
        if self.list_resolutions:
            await self.list_resolutions_and_exit()
        await self.handle_r_flag()

    async def list_resolutions_and_exit(self) -> None:
        """List available resolutions for a video and exit."""
        for url in self.urls:
            if is_video(url):
                print(f"Dostępne rozdzielczości dla {url}:")
                async with ClientSession(headers=self.headers) as session:
                    v = Video(
                        url,
                        self.directory,
                        self.resolution,
                        self.driver_path,
                        self.headers,
                        session,
                    )
                    v.video_id = v.get_videoid()
                    resolutions = await v.get_resolutions()
                    for res in resolutions:
                        print(res)
            elif is_folder(url):
                exit(
                    f"Flaga -R jest dostępna tylko dla filmów. {url} jest"
                    " folderem!"
                )
            else:
                exit(f"Nie rozpoznano adresu url: {url}")
        exit()

    async def handle_r_flag(self) -> None:
        for url in self.urls:
            if self.resolution != "najlepsza":
                if is_video(url):
                    async with ClientSession(headers=self.headers) as session:
                        v = Video(
                            url,
                            self.directory,
                            self.resolution,
                            self.driver_path,
                            self.headers,
                            session,
                        )
                        v.video_id = v.get_videoid()
                        v.resolutions = await v.get_resolutions()
                        v.check_resolution()
                elif is_folder(url):
                    exit(
                        f"Flaga -r jest dostępna tylko dla filmów. {url} jest"
                        " folderem!"
                    )
                else:
                    exit(f"Nie rozpoznano adresu url: {url}")

    async def install_and_get_driver_path(self) -> str:
        return ChromeDriverManager().install()

    def get_urls(self) -> tuple[list[str], list[str]]:
        video_urls: list[str] = []
        folder_urls: list[str] = []
        for url in self.urls:
            if is_video(url):
                video_urls.append(url)
            elif is_folder(url):
                folder_urls.append(url)
            else:
                print(f"Nie rozpoznano adresu url: {url}")
        return video_urls, folder_urls

    async def download_folders(self) -> None:
        async with ClientSession(headers=self.headers) as session:
            for folder_url in self.folder_urls:
                await Folder(
                    folder_url,
                    self.directory,
                    self.driver_path,
                    self.headers,
                    session,
                ).download_folder()

    async def download_videos(self) -> None:
        async with ClientSession(headers=self.headers) as session:
            limit = asyncio.Semaphore(3)

            async def wrapper(video_url: str) -> None:
                async with limit:
                    await Video(
                        video_url,
                        self.directory,
                        self.resolution,
                        self.driver_path,
                        self.headers,
                        session,
                    ).download_video()

            tasks = [
                asyncio.create_task(wrapper(video_url))
                for video_url in self.video_urls
            ]
            await asyncio.gather(*tasks)
