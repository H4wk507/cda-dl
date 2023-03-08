from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup

from cda_dl.download_options import DownloadOptions
from cda_dl.download_state import DownloadState
from cda_dl.error import HTTPError, ParserError
from cda_dl.ui import RichUI
from cda_dl.utils import get_folder_match, get_request, get_safe_title
from cda_dl.video import Video


class Folder:
    title: str
    videos: list[Video]
    folders: list[Folder]
    soup: BeautifulSoup

    def __init__(
        self, url: str, session: aiohttp.ClientSession, ui: RichUI
    ) -> None:
        self.url = url
        self.url = self.get_adjusted_url()
        self.session = session
        self.ui = ui
        self.headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

    def get_adjusted_url(self) -> str:
        """If the url has no page specified, add /1/ at the
        end of it, indicating that we start from the page 1."""
        if not self.url.endswith("/"):
            self.url += "/"
        match = get_folder_match(self.url)
        return self.url if match and match.group(2) else self.url + "1/"

    async def download_folder(
        self, download_options: DownloadOptions, download_state: DownloadState
    ) -> None:
        """Recursively download all videos and subfolders of the folder."""
        self.soup = await self.get_soup()
        self.title = await self.get_folder_title()
        await self.make_directory(download_options)
        self.folders = await self.get_subfolders()
        self.videos = await self.get_videos_from_folder()
        assert self.ui.progbar_folder
        self.ui.add_task_folder(
            self.title, len(self.folders) + len(self.videos)
        )
        if len(self.videos) > 0:
            await self.download_videos_from_folder(
                download_options, download_state
            )
        if len(self.folders) > 0:
            await self.download_subfolders(download_options, download_state)
        self.ui.remove_task_folder()

    async def download_subfolders(
        self, download_options: DownloadOptions, download_state: DownloadState
    ) -> None:
        """Download all subfolders of the folder."""
        for folder in self.folders:
            await folder.download_folder(download_options, download_state)
            assert self.ui.progbar_folder
            self.ui.update_task_folder(1)

    async def get_soup(self) -> BeautifulSoup:
        response = await get_request(self.url, self.session, self.headers)
        text = await response.text()
        soup = BeautifulSoup(text, "html.parser")
        return soup

    async def make_directory(self, download_options: DownloadOptions) -> None:
        """Make directory for the folder."""
        download_options.directory = Path(
            download_options.directory, self.title
        )
        download_options.directory.mkdir(parents=True, exist_ok=True)

    async def get_folder_title(self) -> str:
        try:
            title_wrapper = self.soup.find_all(
                "span", class_="folder-one-line"
            )[-1]
        except IndexError:
            raise ParserError(
                f"Error podczas parsowania 'folder title' dla {self.url}"
                " Pomijam ..."
            )
        title = title_wrapper.find("a", href=True).text
        return get_safe_title(title)

    async def get_subfolders(self) -> list[Folder]:
        """Get subfolders of the folder."""
        folders_soup = self.soup.find_all(
            "a", href=True, class_="object-folder"
        )
        folders = [
            Folder(folder["href"], self.session, self.ui)
            for folder in folders_soup
            if "data-foldery_id" in folder.attrs
        ]
        return folders

    async def download_videos_from_folder(
        self, download_options: DownloadOptions, download_state: DownloadState
    ) -> None:
        """Download all videos from the folder."""
        if self.ui.progbar_video is None:
            self.ui.set_progress_bar_video("bold blue")
            self.ui.add_row_video("green")

        async def wrapper(video: Video) -> None:
            async with download_options.semaphore:
                await video.download_video(download_options, download_state)
                assert self.ui.progbar_folder
                self.ui.update_task_folder(1)

        tasks = [asyncio.create_task(wrapper(video)) for video in self.videos]
        await asyncio.gather(*tasks)

    async def get_videos_from_folder(self) -> list[Video]:
        """Get all videos from the folder."""
        all_videos: list[Video] = []
        while True:
            try:
                videos = await self.get_videos_from_current_page()
            except HTTPError:
                break
            all_videos.extend(videos)
            self.url = self.get_next_page_url()
        return all_videos

    async def get_videos_from_current_page(self) -> list[Video]:
        """Get all videos from the current page."""
        response = await get_request(self.url, self.session, self.headers)
        text = await response.text()
        page_soup = BeautifulSoup(text, "html.parser")
        videos_soup = page_soup.find_all(
            "a", href=True, class_="thumbnail-link"
        )
        videos = [
            Video(
                "https://www.cda.pl" + video["href"],
                self.session,
                self.ui,
            )
            for video in videos_soup
        ]
        return videos

    def get_next_page_url(self) -> str:
        """Get next page of the folder."""
        match = get_folder_match(self.url)
        assert match
        page_number = int(match.group(2))
        stripped_url = match.group(1)
        return stripped_url + "/" + str(page_number + 1) + "/"
