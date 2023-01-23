import argparse
import re
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
from typing import cast

CDA_URL = "https://www.cda.pl"


class Downloader:
    """Class for enclosing all things required to run the downloader."""

    urls: list[str]
    directory: str
    resolution: str
    chrome_options: Options
    driver: webdriver.Chrome

    def __init__(self, args: argparse.Namespace) -> None:
        self.urls = [url.strip() for url in args.urls]
        self.directory = os.path.abspath(
            os.path.expanduser(os.path.expandvars(args.directory))
        )
        self.resolution = args.resolution
        if args.list_resolutions:
            self.list_resolutions_and_exit()
        self.handle_r_flag()

        self.main()

    def list_resolutions_and_exit(self) -> None:
        """List available resolutions for a video and exit."""
        for url in self.urls:
            if Downloader.is_folder(url):
                exit(
                    f"Flaga -R jest dostępna tylko dla filmów. {url} jest folderem!"
                )
            elif Downloader.is_video(url):
                print(f"Dostępne rozdzielczości dla {url}:")
                # Webdriver is not needed for listing resolutions.
                resolutions = Video(
                    url,
                    self.directory,
                    self.resolution,
                    cast(webdriver.Chrome, None),
                ).get_resolutions()
                for res in resolutions:
                    print(res)
            else:
                exit(f"Nie rozpoznano adresu url: {url}")
        exit()

    def handle_r_flag(self) -> None:
        for url in self.urls:
            if self.resolution != "najlepsza":
                if Downloader.is_folder(url):
                    exit(
                        f"Flaga -r jest dostępna tylko dla filmów. {url} jest folderem!"
                    )
                elif Downloader.is_video(url):
                    # Check if resolution is available without installing the webdriver.
                    v = Video(
                        url,
                        self.directory,
                        self.resolution,
                        cast(webdriver.Chrome, None),
                    )
                    v.resolutions = v.get_resolutions()
                    v.check_resolution()
                else:
                    exit(f"Nie rozpoznano adresu url: {url}")

    def main(self) -> None:
        for url in self.urls:
            if Downloader.is_video(url):
                self.init_webdriver()
                Video(
                    url, self.directory, self.resolution, self.driver
                ).download_video()
            elif Downloader.is_folder(url):
                self.init_webdriver()
                Folder(url, self.directory, self.driver).download_folder()
            else:
                exit(f"Nie rozpoznano adresu url: {url}")

    @staticmethod
    def is_video(url: str) -> bool:
        """Check if url is a cda video."""
        video_regex = r"cda\.pl\/video\/\w+\/?$"
        return re.search(video_regex, url, re.IGNORECASE) is not None

    @staticmethod
    def is_folder(url: str) -> bool:
        """Check if url is a cda folder."""
        folder_regex = r"cda\.pl\/.+\/folder\/\w+\/?\d+?\/?$"
        return re.search(folder_regex, url, re.IGNORECASE) is not None

    @staticmethod
    def get_adjusted_title(title: str) -> str:
        """Remove characters that are not allowed in the filename."""
        title = re.sub(r"[^\w\s-]", "", title)
        title = re.sub(r"[\s-]+", "_", title).strip("_")
        return title

    def init_webdriver(self) -> None:
        """Initialize the webdriver."""
        os.environ["WDM_LOG"] = str(logging.NOTSET)
        os.environ["WDM_LOCAL"] = "1"
        self.chrome_options = self.get_options()
        self.driver = webdriver.Chrome(
            service=ChromeService(
                ChromeDriverManager(cache_valid_range=1).install()
            ),
            options=self.chrome_options,
        )

    def get_options(self) -> Options:
        """Get options for the webdriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        return chrome_options


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
        directory: str,
        resolution: str,
        driver: webdriver.Chrome,
    ) -> None:
        self.url = url.rstrip("/")
        self.directory = directory
        self.resolution = resolution
        self.driver = driver
        self.video_id = self.get_videoid()

    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        video_regex = r"cda\.pl\/video\/(.+)$"
        match = re.search(video_regex, self.url, re.IGNORECASE)
        return match.group(1) if match else ""

    def download_video(self) -> None:
        self.initialize()
        # Make directory if it does not exist.
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        print(f"Pobieram {self.filepath} [{self.resolution}]")
        self.stream_data()
        print(f"Skończono pobieranie {self.title}.mp4")

    def initialize(self) -> None:
        """Initialize members required to download the Video."""
        self.resolutions = self.get_resolutions()
        self.resolution = self.get_adjusted_resolution()
        self.check_resolution()
        self.driver.get(
            f"https://ebd.cda.pl/1920x1080/{self.video_id}/?wersja={self.resolution}"
        )
        self.video_soup = BeautifulSoup(self.driver.page_source, "html.parser")
        self.video_stream = self.get_video_stream()
        self.title = self.get_title()
        self.filepath = self.get_filepath()

    def get_resolutions(self) -> list[str]:
        """Get available Video resolutions at the url."""
        response = requests.get(self.url)
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
        """Check if Video resolution is available
        from the list of resolutions."""
        return self.resolution in self.resolutions

    def get_adjusted_resolution(self) -> str:
        if self.resolution == "najlepsza":
            return self.get_best_resolution()
        else:
            return self.resolution

    def check_resolution(self) -> None:
        """Check if resolution is correct."""
        if not self.is_valid_resolution():
            exit(
                f"{self.resolution} rozdzielczość nie jest dostępna dla {self.url}"
            )

    def get_video_stream(self) -> requests.Response:
        video = self.video_soup.find("video")
        if not isinstance(video, Tag):
            exit("Error podczas parsowania 'video stream'")
        src = video["src"]
        if not isinstance(src, str):
            exit("Error podczas parsowania 'video stream'")
        video_stream = requests.get(src, stream=True)
        return video_stream

    def get_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            exit("Error podczas parsowania 'title'")
        title = title_tag.text.strip("\n")
        return Downloader.get_adjusted_title(title)

    def get_filepath(self) -> str:
        return os.path.join(self.directory, f"{self.title}.mp4")

    def stream_data(self) -> None:
        with open(self.filepath, "wb") as f:
            for chunk in self.video_stream.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk is not None:
                    f.write(chunk)


class Folder:
    title: str
    folder_soup: BeautifulSoup
    videos: ResultSet[Tag]

    def __init__(
        self,
        url: str,
        directory: str,
        driver: webdriver.Chrome,
    ) -> None:
        self.url = url
        self.url = self.get_adjusted_url()
        self.directory = directory
        self.driver = driver

    def get_adjusted_url(self) -> str:
        """If the url has no page specified, add /1/ at the
        end of it, indicating that we start from the page 1."""
        if not self.url.endswith("/"):
            self.url += "/"
        folder_regex = r"cda\.pl\/.+\/folder\/\w+\/(\d+\/)?$"
        match = re.search(folder_regex, self.url, re.IGNORECASE)
        assert match
        if match.group(1) is None:
            return self.url + "1/"
        else:
            return self.url

    def get_folder_title(self) -> str:
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")
        try:
            title_wrapper = soup.find_all("span", class_="folder-one-line")[-1]
        except IndexError:
            exit("Error podczas parsowania 'folder title'")
        title = title_wrapper.find("a", href=True).text
        return Downloader.get_adjusted_title(title)

    def get_page_soup(self) -> BeautifulSoup:
        page_soup = BeautifulSoup(self.driver.page_source, "html.parser")
        return page_soup

    def get_videos_from_current_page(self) -> ResultSet[Tag]:
        """Get all videos from the current page."""
        videos = self.page_soup.find_all(
            "a", href=True, class_="thumbnail-link"
        )
        return videos

    def download_videos_from_current_page(self) -> None:
        """Download all videos from the current page."""
        for video in self.videos:
            href = video["href"]
            if isinstance(href, str):
                video_url = CDA_URL + href
            else:
                video_url = CDA_URL + href[0]
            Video(
                video_url, self.directory, "najlepsza", self.driver
            ).download_video()

    def get_next_page(self) -> str:
        """Get next page of the folder."""
        page_number_regex = r"(\d+)\/$"
        match = re.search(page_number_regex, self.url)
        assert match
        page_number = int(match.group(1))
        return (
            re.sub(page_number_regex, "", self.url)
            + str(page_number + 1)
            + "/"
        )

    def download_folder(self) -> None:
        self.title = self.get_folder_title()
        self.directory = os.path.join(self.directory, self.title)
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        while True:
            self.driver.get(self.url)
            self.page_soup = self.get_page_soup()
            self.videos = self.get_videos_from_current_page()
            if len(self.videos) == 0:
                break
            self.download_videos_from_current_page()
            self.url = self.get_next_page()


# TODO: polishify stdout messages and help
# TODO: write README.md in polish
# TODO: add progress bar for downloading video
# TODO: handle folder of other folders https://www.cda.pl/Pokemon_Odcinki_PL/folder-glowny
# TODO: resume folder download if it was previously cancelled
# TODO: add async
