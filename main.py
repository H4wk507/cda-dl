import argparse
import re
import platform
import json
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from bs4.element import ResultSet, Tag
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging


os.environ["WDM_LOG"] = str(logging.NOTSET)
os.environ["WDM_LOCAL"] = "1"

CDA_URL = "https://www.cda.pl"
USER_OS = platform.system()


class Downloader:
    """Class for enclosing all things required to run the downloader."""

    url: str
    directory: str
    resolution: str
    list_resolutions: bool
    chrome_options: Options
    driver: webdriver.Chrome

    def __init__(self, args: argparse.Namespace) -> None:
        self.url = args.url
        self.directory = os.path.abspath(
            os.path.expanduser(os.path.expandvars(args.directory))
        )
        self.resolution = args.resolution
        self.list_resolutions = args.list_resolutions

        self.chrome_options = self.get_options()
        self.driver = webdriver.Chrome(
            service=ChromeService(
                ChromeDriverManager(cache_valid_range=1).install()
            ),
            options=self.chrome_options,
        )
        self.main()

    def get_options(self) -> Options:
        """Get options for the webdriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        return chrome_options

    def main(self) -> None:
        if self.list_resolutions:
            self.list_resolutions_and_exit()
        elif self.is_video():
            Video(
                self.url, self.driver, self.directory, self.resolution
            ).download_video()
        elif self.is_folder():
            if self.resolution != "best":
                exit("-r flag is only available for videos.")
            Folder(self.url, self.driver, self.directory).download_folder()
        else:
            print("Could not recognize the url. Aborting...")

    def list_resolutions_and_exit(self) -> None:
        """List available resolutions for a video and exit."""
        if not self.is_video():
            print("-R flag is only available for videos.")
        else:
            print(f"Available resolutions for {self.url}:")
            resolutions = Video(
                self.url, self.driver, self.directory, self.resolution
            ).get_resolutions()
            for res in resolutions:
                print(res)
        exit()

    def is_video(self) -> bool:
        """Check if url is a cda video."""
        video_regex = r"cda\.pl\/video\/.+$"
        return re.search(video_regex, self.url) is not None

    def is_folder(self) -> bool:
        """Check if url is a cda folder."""
        folder_regex = r"cda\.pl\/.+\/folder\/.+$"
        return re.search(folder_regex, self.url) is not None


class Video:
    video_id: str
    resolutions: list[str]
    video_soup: BeautifulSoup
    video_stream: requests.Response
    title: str
    filepath: str

    def __init__(
        self,
        url: str,
        driver: webdriver.Chrome,
        directory: str,
        resolution: str,
    ) -> None:
        self.url = url
        self.driver = driver
        self.directory = directory
        self.resolution = resolution
        self.video_id = self.get_videoid()
        self.resolutions = self.get_resolutions()
        self.resolution = self.get_adjusted_resolution()
        self.check_resolution()

    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        video_regex = r"cda\.pl\/video\/(.+)$"
        match = re.search(video_regex, self.url)
        return match.group(1) if match else ""

    def get_resolutions(self) -> list[str]:
        """Get available Video resolutions at the url."""
        response = requests.get(self.url)
        video_soup = BeautifulSoup(response.text, "html.parser")
        media_player = video_soup.find(
            "div", {"id": f"mediaplayer{self.video_id}"}
        )
        if not isinstance(media_player, Tag):
            exit("Error while parsing media player")
        video_info = json.loads(media_player.attrs["player_data"])
        resolutions = video_info["video"]["qualities"]
        return list(resolutions)

    def get_best_resolution(self) -> str:
        """Get best Video resolution available at the url."""
        return self.resolutions[-1]

    def is_valid_resolution(self) -> bool:
        """Check if Video resolution is available
        from the list of resolutions."""
        return self.resolution in self.resolutions

    def get_adjusted_resolution(self) -> str:
        if self.resolution == "best":
            return self.get_best_resolution()
        else:
            return self.resolution

    def check_resolution(self) -> None:
        """Check if resolution is correct."""
        if not self.is_valid_resolution():
            exit(
                f"{self.resolution} resolution is not available for {self.url}"
            )

    def download_video(self) -> None:
        self.initialize()
        # Make directory if it does not exist.
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        print(f"Downloading {self.filepath} [{self.resolution}]")
        self.stream_data()
        print(f"Finished downloading {self.title}.mp4")

    def initialize(self) -> None:
        """Initialize members required to download the Video."""
        self.driver.get(
            f"https://ebd.cda.pl/1920x1080/{self.video_id}/?wersja={self.resolution}"
        )
        self.video_soup = BeautifulSoup(self.driver.page_source, "html.parser")
        self.video_stream = self.get_video_stream()
        self.title = self.get_title()
        self.filepath = self.get_filepath()

    def get_video_stream(self) -> requests.Response:
        video = self.video_soup.find("video")
        if not isinstance(video, Tag):
            exit("Error while parsing video stream")
        src = video["src"]
        if not isinstance(src, str):
            exit("Error while parsing video stream")
        video_stream = requests.get(src, stream=True)
        return video_stream

    def get_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            exit("Error while parsing title")
        title = title_tag.text.strip("\n")
        return self.adjust_title(title)

    def adjust_title(self, title: str) -> str:
        """Different operating systems do not allow certain
        characters in the filename, so remove them."""
        title = title.replace(" ", "_")
        if USER_OS == "Windows":
            title = re.sub(r'[<>:"\/\\|?*.]', "", title)
        elif USER_OS == "Darwin":
            title = re.sub(r"[:\/]", "", title)
        else:
            title = re.sub(r"[\/]", "", title)
        return title

    def get_filepath(self) -> str:
        if USER_OS == "Windows":
            filepath = rf"{self.directory}\{self.title}.mp4"
        else:
            filepath = rf"{self.directory}/{self.title}.mp4"
        return filepath

    def stream_data(self) -> None:
        with open(self.filepath, "wb") as f:
            for chunk in self.video_stream.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk is not None:
                    f.write(chunk)


class Folder:
    folder_soup: BeautifulSoup
    videos: ResultSet[Tag]

    def __init__(
        self,
        url: str,
        driver: webdriver.Chrome,
        directory: str,
    ) -> None:
        self.url = url
        self.driver = driver
        self.directory = directory

        self.driver.get(self.url)
        self.folder_soup = BeautifulSoup(
            self.driver.page_source, "html.parser"
        )
        self.videos = self.get_videos()

    def get_videos(self) -> ResultSet[Tag]:
        videos = self.folder_soup.find_all(
            "a", href=True, class_="thumbnail-link"
        )
        return videos

    def download_folder(self) -> None:
        for video in self.videos:
            video_url = CDA_URL + video["href"][0]
            Video(
                video_url, self.driver, self.directory, resolution="best"
            ).download_video()


# TODO: add progress bar for downloading video
# TODO: when downloading folder traverse next pages
# TODO: resume folder download if it was previously cancelled
# TODO: multiple urls
# TODO: add async
# url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
# url = "https://www.cda.pl/video/9122600a"
