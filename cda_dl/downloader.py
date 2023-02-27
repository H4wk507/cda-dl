import argparse
import asyncio
import logging
import sys
from os import path
from pathlib import Path

import aiohttp
from rich.live import Live
from rich.table import Table

from cda_dl.error import (
    FlagError,
    GeoBlockedError,
    HTTPError,
    LoginRequiredError,
    ParserError,
    ResolutionError,
)
from cda_dl.folder import Folder
from cda_dl.ui import RichUI
from cda_dl.utils import is_folder, is_video
from cda_dl.video import Video

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler(sys.stdout))


class Downloader:
    urls: list[str]
    directory: Path
    resolution: str
    list_resolutions: bool
    overwrite: bool
    nthreads: int
    ui: RichUI
    semaphore: asyncio.Semaphore

    def __init__(self, args: argparse.Namespace) -> None:
        self.urls = [url.strip() for url in args.urls]
        self.directory = Path(
            path.abspath(path.expanduser(path.expandvars(args.directory)))
        )
        self.resolution = args.resolution
        self.list_resolutions = args.list_resolutions
        self.overwrite = args.overwrite
        self.nthreads = args.nthreads
        self.ui = RichUI(Table.grid(expand=True))
        asyncio.run(self.main())

    async def main(self) -> None:
        async with aiohttp.ClientSession() as session:
            try:
                if self.list_resolutions:
                    await self.list_resolutions_and_exit(session)
                await self.check_valid_resolution(session)
                self.set_threads()
            except (FlagError, ResolutionError) as e:
                LOGGER.error(e)
            else:
                self.video_urls, self.folder_urls = self.get_urls()
                with Live(self.ui.table, refresh_per_second=10):
                    if len(self.folder_urls) > 0:
                        await self.download_folders(session)
                    if len(self.video_urls) > 0:
                        await self.download_videos(session)
                # TODO: when the download is finished, the empty rows of the
                # table are still present, we could clear the whole terminal
                # after download but then how do we handle bugs printed to
                # the terminal?
                LOGGER.info("Skończono pobieranie wszystkich plików.")

    async def list_resolutions_and_exit(
        self, session: aiohttp.ClientSession
    ) -> None:
        """List available resolutions for a video and exit."""
        for url in self.urls:
            if is_video(url):
                await Video(
                    url, self.directory, self.resolution, session, self.ui
                ).list_resolutions()
            elif is_folder(url):
                LOGGER.warning(
                    f"Opcja -R jest dostępna tylko dla filmów. {url} jest"
                    " folderem!"
                )
            else:
                LOGGER.warning(f"Nie rozpoznano adresu url: {url}")
            sys.exit()

    def changed_resolution(self) -> bool:
        """Check if resolution was changed by the user."""
        return self.resolution != "najlepsza"

    async def check_valid_resolution(
        self, session: aiohttp.ClientSession
    ) -> None:
        """Check if the resolution provided by the user is valid."""
        for url in self.urls:
            if self.changed_resolution():
                if is_video(url):
                    await Video(
                        url, self.directory, self.resolution, session, self.ui
                    ).check_resolution()
                elif is_folder(url):
                    raise FlagError(
                        f"Opcja -r jest dostępna tylko dla filmów. {url} jest"
                        " folderem!"
                    )
                else:
                    raise FlagError(f"Nie rozpoznano adresu url: {url}")

    def set_threads(self) -> None:
        """Set number of threads for download."""
        if self.nthreads <= 0:
            raise FlagError(
                f"Opcja -t musi być większa od 0. Podano: {self.nthreads}."
            )
        self.semaphore = asyncio.Semaphore(self.nthreads)

    def get_urls(self) -> tuple[list[str], list[str]]:
        """Split urls into two lists: video_urls and folder_urls."""
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
        self.ui.set_progress_bar_folder("bold yellow")
        self.ui.add_row_folder("green")
        for folder_url in self.folder_urls:
            try:
                await Folder(
                    folder_url, self.directory, session, self.ui
                ).download_folder(self.semaphore, self.overwrite)
            except (ParserError, HTTPError) as e:
                LOGGER.warning(e)

    async def download_videos(self, session: aiohttp.ClientSession) -> None:
        if self.ui.progbar_video is None:
            self.ui.set_progress_bar_video("bold blue")
            self.ui.add_row_video("green")

        async def wrapper(video_url: str) -> None:
            async with self.semaphore:
                try:
                    await Video(
                        video_url,
                        self.directory,
                        self.resolution,
                        session,
                        self.ui,
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
