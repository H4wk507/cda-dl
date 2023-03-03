import json
import logging
import re
from pathlib import Path
from typing import Any

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag
from rich.logging import RichHandler

from cda_dl.error import (
    GeoBlockedError,
    LoginRequiredError,
    ParserError,
    ResolutionError,
)
from cda_dl.ui import RichUI
from cda_dl.utils import (
    decrypt_url,
    get_request,
    get_safe_title,
    get_video_match,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False)],
)
LOGGER = logging.getLogger(__name__)


class Video:
    video_id: str
    resolutions: list[str]
    video_soup: BeautifulSoup
    video_info: Any
    file: str
    video_stream: aiohttp.ClientResponse
    remaining_size: int
    title: str
    filepath: Path
    partial_filepath: Path
    resume_point: int

    def __init__(
        self,
        url: str,
        directory: Path,
        resolution: str,
        session: aiohttp.ClientSession,
        ui: RichUI,
    ) -> None:
        self.url = url
        self.directory = directory
        self.resolution = resolution
        self.session = session
        self.ui = ui
        self.headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

    async def download_video(self, overwrite: bool) -> None:
        await self.initialize()
        if self.filepath.exists() and not overwrite:
            LOGGER.info(f"Plik '{self.title}.mp4' już istnieje. Pomijam ...")
        else:
            self.make_directory()
            await self.stream_file()

    async def initialize(self) -> None:
        """Initialize members required to download the Video."""
        self.video_id = self.get_videoid()
        self.video_soup = await self.get_video_soup()
        self.title = self.get_video_title()
        self.filepath = self.get_filepath()
        self.partial_filepath = self.get_partial_filepath()
        self.check_premium()
        self.check_geolocation()
        self.video_info = await self.get_video_info()
        self.resolutions = self.get_resolutions()
        self.resolution = self.get_adjusted_resolution()
        self.raise_invalid_res()
        self.file = self.get_file()
        self.resume_point = self.get_resume_point()
        self.video_stream = await self.get_video_stream()
        self.remaining_size = self.get_remaining_size()

    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        match = get_video_match(self.url)
        assert match
        return match.group(1)

    async def get_video_soup(self) -> BeautifulSoup:
        response = await get_request(self.url, self.session, self.headers)
        text = await response.text()
        return BeautifulSoup(text, "html.parser")

    def get_video_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            raise ParserError(
                "Error podczas parsowania 'video title'. Pomijam ..."
            )
        title = title_tag.text.strip("\n")
        return get_safe_title(title)

    def get_filepath(self) -> Path:
        return Path(self.directory, f"{self.title}.mp4")

    def get_partial_filepath(self) -> Path:
        return self.filepath.parent / f"{self.filepath.name}.part"

    def check_premium(self) -> None:
        if re.search(
            "Ten film jest dostępny dla użytkowników premium",
            self.video_soup.text,
        ):
            raise LoginRequiredError(
                "Ten film jest dostępny tylko dla użytkowników premium."
                " Pomijam ..."
            )

    def check_geolocation(self) -> None:
        if re.search(
            r"niedostępn[ey] w(?:&nbsp;|\s+)Twoim kraju\s*",
            self.video_soup.text,
        ):
            raise GeoBlockedError(
                "To wideo jest niedostępne w Twoim kraju. Pomijam ..."
            )

    async def get_video_info(self) -> Any:
        """Get Video info from the url."""
        media_player = self.video_soup.find(
            "div", {"id": f"mediaplayer{self.video_id}"}
        )
        if not isinstance(media_player, Tag):
            raise ParserError(
                "Error podczas parsowania 'media player'. Pomijam ..."
            )
        player_data = json.loads(media_player.attrs["player_data"])
        return player_data["video"]

    def get_resolutions(self) -> list[str]:
        """Get available Video resolutions at the url."""
        return list(self.video_info["qualities"])

    async def list_resolutions(self) -> None:
        self.video_id = self.get_videoid()
        self.video_soup = await self.get_video_soup()
        self.video_info = await self.get_video_info()
        resolutions = self.get_resolutions()
        LOGGER.info(f"Dostępne rozdzielczości dla {self.url}:")
        for res in resolutions:
            LOGGER.info(res)

    async def check_resolution(self) -> None:
        self.video_id = self.get_videoid()
        self.video_soup = await self.get_video_soup()
        self.video_info = await self.get_video_info()
        self.resolutions = self.get_resolutions()
        self.raise_invalid_res()

    def get_best_resolution(self) -> str:
        """Get best Video resolution available at the url."""
        return self.resolutions[-1]

    def is_valid_resolution(self) -> bool:
        return self.resolution in self.resolutions

    def get_adjusted_resolution(self) -> str:
        return (
            self.get_best_resolution()
            if self.resolution == "najlepsza"
            else self.resolution
        )

    def raise_invalid_res(self) -> None:
        """Raise ResolutionError if resolution is invalid."""
        if not self.is_valid_resolution():
            raise ResolutionError(
                f"{self.resolution} rozdzielczość nie jest dostępna dla"
                f" {self.url}"
            )

    def get_file(self) -> str:
        """Get decrypted link to the file download."""
        return decrypt_url(self.video_info["file"])

    def get_resume_point(self) -> int:
        return (
            self.partial_filepath.stat().st_size
            if self.partial_filepath.exists()
            else 0
        )

    async def get_video_stream(self) -> aiohttp.ClientResponse:
        range_num = f"bytes={self.resume_point}-"
        self.headers["Range"] = range_num
        video_stream = await get_request(self.file, self.session, self.headers)
        return video_stream

    def get_remaining_size(self) -> int:
        """Get remaining Video size in KiB."""
        return int(self.video_stream.headers.get("content-length", 0))

    def make_directory(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    async def stream_file(self) -> None:
        block_size = 1024
        desc = f"{self.title}.mp4 [{self.resolution}]"
        self.filepath.unlink(missing_ok=True)
        assert self.ui.progbar_video
        task_id = self.ui.progbar_video.add_task(
            "download",
            filename=desc,
            total=self.resume_point + self.remaining_size,
            completed=self.resume_point,
        )
        async with aiofiles.open(self.partial_filepath, "ab") as f:
            async for chunk in self.video_stream.content.iter_chunked(
                block_size * block_size
            ):
                await f.write(chunk)
                self.ui.progbar_video.update(task_id, advance=len(chunk))
        self.partial_filepath.rename(self.filepath)
        self.ui.progbar_video.remove_task(task_id)
