import argparse
import asyncio
import logging
import os
import sys

import aiohttp

from cda_dl.error import (
    FlagError,
    GeoBlockedError,
    HTTPError,
    LoginRequiredError,
    ParserError,
    ResolutionError,
)
from cda_dl.folder import Folder
from cda_dl.utils import is_folder, is_video
from cda_dl.video import Video

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler(sys.stdout))


class Downloader:
    urls: list[str]
    directory: str
    resolution: str
    list_resolutions: bool
    overwrite: bool
    semaphore: asyncio.Semaphore

    def __init__(self, args: argparse.Namespace) -> None:
        self.urls = [url.strip() for url in args.urls]
        self.directory = os.path.abspath(
            os.path.expanduser(os.path.expandvars(args.directory))
        )
        self.resolution = args.resolution
        self.list_resolutions = args.list_resolutions
        self.overwrite = args.overwrite
        self.semaphore = asyncio.Semaphore(3)
        asyncio.run(self.main())

    async def main(self) -> None:
        async with aiohttp.ClientSession() as session:
            try:
                await self.handle_flags(session)
            except (FlagError, ResolutionError) as e:
                LOGGER.error(e)
            else:
                self.video_urls, self.folder_urls = self.get_urls()
                await self.download_folders(session)
                await self.download_videos(session)
                LOGGER.info("Skończono pobieranie wszystkich plików.")

    async def handle_flags(self, session: aiohttp.ClientSession) -> None:
        if self.list_resolutions:
            await self.list_resolutions_and_exit(session)
        await self.handle_r_flag(session)

    async def list_resolutions_and_exit(
        self, session: aiohttp.ClientSession
    ) -> None:
        """List available resolutions for a video and exit."""
        for url in self.urls:
            if is_video(url):
                LOGGER.info(f"Dostępne rozdzielczości dla {url}:")
                v = Video(
                    url,
                    self.directory,
                    self.resolution,
                    session,
                )
                v.video_id = v.get_videoid()
                v.video_soup = await v.get_video_soup()
                v.video_info = await v.get_video_info()
                resolutions = await v.get_resolutions()
                for res in resolutions:
                    LOGGER.info(res)
            elif is_folder(url):
                LOGGER.warning(
                    f"Flaga -R jest dostępna tylko dla filmów. {url} jest"
                    " folderem!"
                )
            else:
                LOGGER.warning(f"Nie rozpoznano adresu url: {url}")
            sys.exit()

    async def handle_r_flag(self, session: aiohttp.ClientSession) -> None:
        for url in self.urls:
            if self.resolution != "najlepsza":
                if is_video(url):
                    v = Video(
                        url,
                        self.directory,
                        self.resolution,
                        session,
                    )
                    v.video_id = v.get_videoid()
                    v.video_soup = await v.get_video_soup()
                    v.video_info = await v.get_video_info()
                    v.resolutions = await v.get_resolutions()
                    v.check_resolution()
                elif is_folder(url):
                    raise FlagError(
                        f"Flaga -r jest dostępna tylko dla filmów. {url} jest"
                        " folderem!"
                    )
                else:
                    raise FlagError(f"Nie rozpoznano adresu url: {url}")

    def get_urls(self) -> tuple[list[str], list[str]]:
        video_urls: list[str] = []
        folder_urls: list[str] = []
        for url in self.urls:
            if is_video(url):
                video_urls.append(url)
            elif is_folder(url):
                folder_urls.append(url)
            else:
                LOGGER.warning(f"Nie rozpoznano adresu url: {url}")
        return video_urls, folder_urls

    async def download_folders(self, session: aiohttp.ClientSession) -> None:
        for folder_url in self.folder_urls:
            try:
                await Folder(
                    folder_url,
                    self.directory,
                    session,
                ).download_folder(self.semaphore, self.overwrite)
            except (ParserError, HTTPError) as e:
                LOGGER.warning(e)

    async def download_videos(self, session: aiohttp.ClientSession) -> None:
        async def wrapper(video_url: str) -> None:
            async with self.semaphore:
                try:
                    await Video(
                        video_url,
                        self.directory,
                        self.resolution,
                        session,
                    ).download_video(self.overwrite)
                except (
                    LoginRequiredError,
                    GeoBlockedError,
                    ResolutionError,
                    ParserError,
                    HTTPError,
                ) as e:
                    LOGGER.warning(e)

        tasks = [
            asyncio.create_task(wrapper(video_url))
            for video_url in self.video_urls
        ]
        await asyncio.gather(*tasks)
