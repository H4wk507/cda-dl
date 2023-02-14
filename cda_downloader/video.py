import os
import logging
import json
import aiofiles
from tqdm import tqdm
from selenium import webdriver
from pathlib import Path
from bs4.element import Tag
from bs4 import BeautifulSoup
from aiohttp import ClientResponse, ClientSession
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from cda_downloader.utils import get_safe_title, get_video_match


class Video:
    video_id: str
    resolutions: list[str]
    video_soup: BeautifulSoup
    driver: webdriver.Chrome
    video_stream: ClientResponse
    size: int
    title: str
    filepath: str

    def __init__(
        self,
        url: str,
        directory: str,
        resolution: str,
        driver_path: str,
        headers: dict[str, str],
        session: ClientSession,
    ) -> None:
        self.url = url
        self.directory = directory
        self.resolution = resolution
        self.driver_path = driver_path
        self.headers = headers
        self.session = session

    async def download_video(self) -> None:
        await self.initialize()
        await self.stream_data()

    async def initialize(self) -> None:
        """Initialize members required to download the Video."""
        self.video_id = self.get_videoid()
        self.resolutions = await self.get_resolutions()
        self.resolution = self.get_adjusted_resolution()
        self.check_resolution()
        self.driver = self.get_webdriver()
        self.driver.get(
            f"https://ebd.cda.pl/1920x1080/{self.video_id}/?wersja={self.resolution}"
        )
        self.video_soup = BeautifulSoup(self.driver.page_source, "html.parser")
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

    async def get_resolutions(self) -> list[str]:
        """Get available Video resolutions at the url."""
        response = await self.session.get(self.url, headers=self.headers)
        video_soup = BeautifulSoup(await response.text(), "html.parser")
        media_player = video_soup.find(
            "div", {"id": f"mediaplayer{self.video_id}"}
        )
        if not isinstance(media_player, Tag):
            exit("Error podczas parsowania 'media player'")
        video_info = json.loads(media_player.attrs["player_data"])
        resolutions = video_info["video"]["qualities"]
        return list(resolutions)

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

    def get_webdriver(self) -> webdriver.Chrome:
        os.environ["WDM_LOG"] = str(logging.NOTSET)
        os.environ["WDM_LOCAL"] = "1"
        options = self.get_options()
        driver = webdriver.Chrome(
            service=ChromeService(self.driver_path), options=options
        )
        return driver

    def get_options(self) -> Options:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--log-level=3")
        return options

    async def get_video_stream(self) -> ClientResponse:
        video = self.video_soup.find("video")
        if not isinstance(video, Tag):
            exit("Error podczas parsowania 'video stream'")
        src = video.get("src", None)
        if not isinstance(src, str):
            exit("Error podczas parsowania 'video stream'")
        video_stream = await self.session.get(src, headers=self.headers)
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
