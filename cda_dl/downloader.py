import argparse
import asyncio
import logging
import sys
from getpass import getpass
from os import path
from pathlib import Path

import aiohttp
from rich.console import Console
from rich.live import Live
from rich.logging import RichHandler
from rich.table import Table

from cda_dl.download_options import DownloadOptions
from cda_dl.download_state import DownloadState
from cda_dl.error import (
    CaptchaError,
    FlagError,
    HTTPError,
    LoginError,
    ParserError,
    ResolutionError,
)
from cda_dl.folder import Folder
from cda_dl.ui import RichUI
from cda_dl.utils import clear, get_random_agent, is_folder, is_video
from cda_dl.video import Video

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False)],
)
LOGGER = logging.getLogger(__name__)


class Downloader:
    urls: list[str]
    login: str | None
    password: str | None
    list_resolutions: bool
    download_options: DownloadOptions
    download_state: DownloadState
    ui: RichUI
    video_urls: list[str]
    folder_urls: list[str]

    def __init__(self, args: argparse.Namespace) -> None:
        self.urls = [url.strip() for url in args.urls]
        self.login, self.password = args.login, None
        if self.login is not None:
            self.password = getpass(f"Podaj hasło dla {self.login}: ")
        self.list_resolutions = args.list_resolutions
        self.download_options = DownloadOptions(
            Path(
                path.abspath(path.expanduser(path.expandvars(args.directory)))
            ),
            args.resolution,
            args.overwrite,
            args.nthreads,
            args.quiet,
        )
        self.download_state = DownloadState()
        self.ui = RichUI(Table.grid(expand=True))
        asyncio.run(self.main())

    async def main(self) -> None:
        async with aiohttp.ClientSession() as session:
            try:
                if self.login is not None and self.password is not None:
                    await self.perform_login(session)
                if self.list_resolutions:
                    await self.list_resolutions_and_exit(session)
                await self.check_valid_resolution(session)
                self.set_threads()
            except (FlagError, ResolutionError, LoginError, CaptchaError) as e:
                LOGGER.error(e)
            else:
                self.video_urls, self.folder_urls = self.get_urls()
                with Live(self.ui.table, refresh_per_second=10):
                    if len(self.folder_urls) > 0:
                        await self.download_folders(session)
                    if len(self.video_urls) > 0:
                        await self.download_videos(session)
                clear()
                console = Console()
                console.print(
                    "| [green bold]Pobrane Pliki:"
                    f" {self.download_state.completed}[/] - [yellow"
                    f" bold]Pominięte Pliki: {self.download_state.skipped}[/]"
                    " - [red bold]Nieudane Pliki:"
                    f" {self.download_state.failed}[/] |\n"
                )
                console.print("Skończono pobieranie. Enjoy :)")

    async def perform_login(self, session: aiohttp.ClientSession) -> None:
        """Log in to the session object."""
        data = {"username": self.login, "password": self.password}
        headers = {"User-Agent": get_random_agent()}
        try:
            r = await session.post(
                "https://www.cda.pl/login", headers=headers, data=data
            )
            r.raise_for_status()
        except aiohttp.ClientResponseError as e:
            raise LoginError(
                f"Nie udało się zalogować [{e.status}]: {e.message}."
            )
        text = await r.text()
        if 'Zaznacz pole "Nie jestem robotem"!' in text:
            raise CaptchaError("Nie udało się zalogować z powodu captchy.")
        elif "Zły login lub hasło!" in text:
            raise LoginError(
                "Nie udało się zalogować z powodu błędnego loginu lub hasła."
            )

    async def list_resolutions_and_exit(
        self, session: aiohttp.ClientSession
    ) -> None:
        """List available resolutions for a video and exit."""
        for url in self.urls:
            if is_video(url):
                await Video(url, session, self.ui).list_resolutions()
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
        return self.download_options.resolution != "najlepsza"

    async def check_valid_resolution(
        self, session: aiohttp.ClientSession
    ) -> None:
        """Check if the resolution provided by the user is valid."""
        for url in self.urls:
            if self.changed_resolution():
                if is_video(url):
                    await Video(url, session, self.ui).check_resolution(
                        self.download_options
                    )
                elif is_folder(url):
                    raise FlagError(
                        f"Opcja -r jest dostępna tylko dla filmów. {url} jest"
                        " folderem!"
                    )
                else:
                    raise FlagError(f"Nie rozpoznano adresu url: {url}")

    def set_threads(self) -> None:
        """Set number of threads for download."""
        if self.download_options.nthreads <= 0:
            raise FlagError(
                "Opcja -t musi być większa od 0. Podano:"
                f" {self.download_options.nthreads}."
            )
        self.download_options.semaphore = asyncio.Semaphore(
            self.download_options.nthreads
        )

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
                self.download_state.failed += 1
        return video_urls, folder_urls

    async def download_folders(self, session: aiohttp.ClientSession) -> None:
        self.ui.set_progress_bar_folder("bold yellow")
        self.ui.add_row_folder("green")
        for folder_url in self.folder_urls:
            try:
                await Folder(folder_url, session, self.ui).download_folder(
                    self.download_options, self.download_state
                )
            except (ParserError, HTTPError) as e:
                LOGGER.warning(e)
                self.download_state.failed += 1

    async def download_videos(self, session: aiohttp.ClientSession) -> None:
        if self.ui.progbar_video is None:
            self.ui.set_progress_bar_video("bold blue")
            self.ui.add_row_video("green")

        async def wrapper(video_url: str) -> None:
            async with self.download_options.semaphore:
                await Video(video_url, session, self.ui).download_video(
                    self.download_options, self.download_state
                )

        tasks = [
            asyncio.create_task(wrapper(video_url))
            for video_url in self.video_urls
        ]
        await asyncio.gather(*tasks)
