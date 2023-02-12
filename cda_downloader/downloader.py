import os
import asyncio
import argparse
import aiohttp
from webdriver_manager.chrome import ChromeDriverManager
from cda_downloader.utils import is_video, is_folder
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
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(
                *[self.download_url(url, session) for url in self.urls]
            )
        print("Skończono robotę.")

    async def handle_flags(self) -> None:
        if self.list_resolutions:
            await self.list_resolutions_and_exit()
        await self.handle_r_flag()

    async def install_and_get_driver_path(self) -> str:
        return ChromeDriverManager().install()

    async def list_resolutions_and_exit(self) -> None:
        """List available resolutions for a video and exit."""
        for url in self.urls:
            if is_video(url):
                print(f"Dostępne rozdzielczości dla {url}:")
                async with aiohttp.ClientSession(
                    headers=self.headers
                ) as session:
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
                    async with aiohttp.ClientSession(
                        headers=self.headers
                    ) as session:
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

    async def download_url(
        self, url: str, session: aiohttp.ClientSession
    ) -> None:
        if is_video(url):
            await Video(
                url,
                self.directory,
                self.resolution,
                self.driver_path,
                self.headers,
                session,
            ).download_video()
        elif is_folder(url):
            await Folder(
                url, self.directory, self.driver_path, self.headers, session
            ).download_folder()
        else:
            print(f"Nie rozpoznano adresu url: {url}")
