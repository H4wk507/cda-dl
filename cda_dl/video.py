import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag
from tqdm.asyncio import tqdm

from cda_dl.error import (
    GeoBlockedError,
    LoginRequiredError,
    ParserError,
    ResolutionError,
)
from cda_dl.utils import (
    decrypt_url,
    get_request,
    get_safe_title,
    get_video_match,
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler(sys.stdout))


class Video:
    video_id: str
    resolutions: list[str]
    video_soup: BeautifulSoup
    video_info: Any
    file: str
    video_stream: aiohttp.ClientResponse
    size: int
    title: str
    filepath: str

    def __init__(
        self,
        url: str,
        directory: str,
        resolution: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self.url = url
        self.directory = directory
        self.resolution = resolution
        self.session = session
        self.headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

    async def download_video(self, overwrite: bool) -> None:
        await self.initialize()
        if os.path.exists(self.filepath) and not overwrite:
            LOGGER.info(f"Plik '{self.title}.mp4' już istnieje. Pomijam ...")
        else:
            self.make_directory()
            await self.stream_file()

    async def initialize(self) -> None:
        """Initialize members required to download the Video."""
        self.video_id = self.get_videoid()
        self.video_soup = await self.get_video_soup()
        self.check_premium()
        self.check_geolocation()
        self.video_info = await self.get_video_info()
        self.resolutions = await self.get_resolutions()
        self.resolution = self.get_adjusted_resolution()
        self.check_resolution()
        self.file = await self.get_file()
        self.video_stream = await self.get_video_stream()
        self.size = self.get_size()
        self.title = self.get_video_title()
        self.filepath = self.get_filepath()

    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        match = get_video_match(self.url)
        assert match
        return match.group(1)

    async def get_video_soup(self) -> BeautifulSoup:
        response = await get_request(self.url, self.session, self.headers)
        text = await response.text()
        return BeautifulSoup(text, "html.parser")

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

    async def get_resolutions(self) -> list[str]:
        """Get available Video resolutions at the url."""
        return list(self.video_info["qualities"])

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

    def check_resolution(self) -> None:
        """Check if resolution is correct."""
        if not self.is_valid_resolution():
            raise ResolutionError(
                f"{self.resolution} rozdzielczość nie jest dostępna dla"
                f" {self.url}"
            )

    async def get_file(self) -> str:
        return decrypt_url(self.video_info["file"])

    async def get_video_stream(self) -> aiohttp.ClientResponse:
        video_stream = await get_request(self.file, self.session, self.headers)
        return video_stream

    def get_size(self) -> int:
        """Get Video size in KiB."""
        return int(self.video_stream.headers.get("content-length", 0))

    def get_video_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            raise ParserError(
                "Error podczas parsowania 'video title'. Pomijam ..."
            )
        title = title_tag.text.strip("\n")
        return get_safe_title(title)

    def get_filepath(self) -> str:
        return os.path.join(self.directory, f"{self.title}.mp4")

    def make_directory(self) -> None:
        Path(self.directory).mkdir(parents=True, exist_ok=True)

    async def stream_file(self) -> None:
        block_size = 1024
        filename = f"{self.title}.mp4 [{self.resolution}]"
        async with aiofiles.open(self.filepath, "wb") as f:
            with tqdm(
                total=self.size,
                unit="iB",
                unit_scale=True,
                desc=filename,
                leave=False,
            ) as pbar:
                async for chunk in self.video_stream.content.iter_chunked(
                    block_size * block_size
                ):
                    await f.write(chunk)
                    pbar.update(len(chunk))