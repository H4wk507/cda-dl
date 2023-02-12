from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import os
from pathlib import Path
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from cda_downloader.utils import get_adjusted_title, get_video_match


class Video:
    video_id: str
    resolutions: list[str]
    video_soup: BeautifulSoup
    driver: webdriver.Chrome
    video_stream: requests.Response
    size: int
    title: str
    filepath: str

    def __init__(
        self,
        url: str,
        directory: str,
        resolution: str,
        headers: dict[str, str],
    ) -> None:
        self.url = url
        self.directory = directory
        self.resolution = resolution
        self.headers = headers

    def download_video(self) -> None:
        self.initialize()
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        self.stream_data()

    def initialize(self) -> None:
        """Initialize members required to download the Video."""
        self.video_id = self.get_videoid()
        self.resolutions = self.get_resolutions()
        self.resolution = self.get_adjusted_resolution()
        self.check_resolution()
        self.driver = self.get_webdriver()
        self.driver.get(
            f"https://ebd.cda.pl/1920x1080/{self.video_id}/?wersja={self.resolution}"
        )
        self.video_soup = BeautifulSoup(self.driver.page_source, "html.parser")
        self.video_stream = self.get_video_stream()
        self.size = self.get_size()
        self.title = self.get_title()
        self.filepath = self.get_filepath()

    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        match = get_video_match(self.url)
        assert match
        return match.group(1)

    def get_resolutions(self) -> list[str]:
        """Get available Video resolutions at the url."""
        response = requests.get(self.url, headers=self.headers)
        video_soup = BeautifulSoup(response.text, "html.parser")
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
            service=ChromeService(ChromeDriverManager().install()),
            options=options,
        )
        return driver

    def get_options(self) -> Options:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--log-level=3")
        return options

    def get_video_stream(self) -> requests.Response:
        video = self.video_soup.find("video")
        if not isinstance(video, Tag):
            exit("Error podczas parsowania 'video stream'")
        src = video.get("src", None)
        if not isinstance(src, str):
            exit("Error podczas parsowania 'video stream'")
        video_stream = requests.get(src, stream=True, headers=self.headers)
        return video_stream

    def get_size(self) -> int:
        """Get Video size in KiB."""
        return int(self.video_stream.headers.get("content-length", 0))

    def get_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            exit("Error podczas parsowania 'title'")
        title = title_tag.text.strip("\n")
        return get_adjusted_title(title)

    def get_filepath(self) -> str:
        return os.path.join(self.directory, f"{self.title}.mp4")

    def stream_data(self) -> None:
        block_size = 1024
        file = f"{self.title}.mp4 [{self.resolution}]"
        with open(self.filepath, "wb") as f:
            with tqdm(
                total=self.size,
                unit="iB",
                unit_scale=True,
                desc=file,
                leave=False,
            ) as pbar:
                for chunk in self.video_stream.iter_content(
                    chunk_size=block_size * block_size
                ):
                    if chunk is not None:
                        f.write(chunk)
                        pbar.update(len(chunk))
