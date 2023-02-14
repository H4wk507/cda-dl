import os
import json
from tqdm.asyncio import tqdm
import aiofiles
import aiohttp
from pathlib import Path
from bs4.element import Tag
from bs4 import BeautifulSoup
from typing import Any
from cda_downloader.utils import get_safe_title, get_video_match, decrypt_url


class Video:
    video_id: str
    resolutions: list[str]
    video_soup: BeautifulSoup
    video_info: dict[str, Any]
    video_stream: aiohttp.ClientResponse
    size: int
    title: str
    filepath: str

    def __init__(
        self,
        url: str,
        directory: str,
        resolution: str,
        headers: dict[str, str],
        session: aiohttp.ClientSession,
    ) -> None:
        self.url = url
        self.directory = directory
        self.resolution = resolution
        self.headers = headers
        self.session = session

    async def download_video(self) -> None:
        await self.initialize()
        await self.stream_data()

    async def initialize(self) -> None:
        """Initialize members required to download the Video."""
        self.video_id = self.get_videoid()
        self.video_soup = await self.get_video_soup()
        self.video_info = await self.get_video_info()
        self.resolutions = await self.get_resolutions()
        self.resolution = self.get_adjusted_resolution()
        self.check_resolution()
        self.file = await self.get_file()
        self.video_stream = await self.get_video_stream()
        self.size = self.get_size()
        self.title = self.get_title()
        self.filepath = self.get_filepath()
        self.make_directory()

    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        match = get_video_match(self.url)
        assert match
        return match.group(1)

    async def get_video_soup(self) -> BeautifulSoup:
        async with self.session.get(
            self.url, headers=self.headers
        ) as response:
            text = await response.text()
        return BeautifulSoup(text, "html.parser")

    async def get_video_info(self) -> dict[str, Any]:
        """Get Video info from the url."""
        media_player = self.video_soup.find(
            "div", {"id": f"mediaplayer{self.video_id}"}
        )
        if not isinstance(media_player, Tag):
            exit("Error podczas parsowania 'media player'")
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
            exit(
                f"{self.resolution} rozdzielczość nie jest dostępna dla"
                f" {self.url}"
            )

    async def get_file(self) -> str:
        return decrypt_url(self.video_info["file"])

    async def get_video_stream(self) -> aiohttp.ClientResponse:
        video_stream = await self.session.get(self.file, headers=self.headers)
        return video_stream

    def get_size(self) -> int:
        """Get Video size in KiB."""
        return int(self.video_stream.headers.get("content-length", 0))

    def get_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            exit("Error podczas parsowania 'title'")
        title = title_tag.text.strip("\n")
        return get_safe_title(title)

    def get_filepath(self) -> str:
        return os.path.join(self.directory, f"{self.title}.mp4")

    def make_directory(self) -> None:
        Path(self.directory).mkdir(parents=True, exist_ok=True)

    async def stream_data(self) -> None:
        block_size = 1024
        file = f"{self.title}.mp4 [{self.resolution}]"
        async with aiofiles.open(self.filepath, "wb") as f:
            with tqdm(
                total=self.size,
                unit="iB",
                unit_scale=True,
                desc=file,
                leave=False,
            ) as pbar:
                async for chunk in self.video_stream.content.iter_chunked(
                    block_size * block_size
                ):
                    await f.write(chunk)
                    pbar.update(len(chunk))
