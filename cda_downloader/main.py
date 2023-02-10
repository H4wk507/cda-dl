import argparse
import re
import json
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
from tqdm import tqdm


class Downloader:
    urls: list[str]
    directory: str
    resolution: str

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
            if Downloader.is_video(url):
                print(f"Dostępne rozdzielczości dla {url}:")
                v = Video(url, self.directory, self.resolution)
                v.video_id = v.get_videoid()
                resolutions = v.get_resolutions()
                for res in resolutions:
                    print(res)
            elif Downloader.is_folder(url):
                exit(
                    f"Flaga -R jest dostępna tylko dla filmów. {url} jest"
                    " folderem!"
                )
            else:
                exit(f"Nie rozpoznano adresu url: {url}")
        exit()

    def handle_r_flag(self) -> None:
        for url in self.urls:
            if self.resolution != "najlepsza":
                if Downloader.is_video(url):
                    v = Video(url, self.directory, self.resolution)
                    v.video_id = v.get_videoid()
                    v.resolutions = v.get_resolutions()
                    v.check_resolution()
                elif Downloader.is_folder(url):
                    exit(
                        f"Flaga -r jest dostępna tylko dla filmów. {url} jest"
                        " folderem!"
                    )
                else:
                    exit(f"Nie rozpoznano adresu url: {url}")

    def main(self) -> None:
        for url in self.urls:
            if Downloader.is_video(url):
                Video(url, self.directory, self.resolution).download_video()
            elif Downloader.is_folder(url):
                Folder(url, self.directory).download_folder()
            else:
                exit(f"Nie rozpoznano adresu url: {url}")
        print("Skończono robotę.")

    @staticmethod
    def is_video(url: str) -> bool:
        """Check if url is a cda video."""
        video_regex = re.compile(
            r"""https?://(?:(?:www|ebd)\.)?cda\.pl/
            (?:video|[0-9]+x[0-9]+)/([0-9a-z]+)""",
            re.VERBOSE | re.IGNORECASE,
        )
        match = video_regex.match(url)
        return match is not None

    @staticmethod
    def is_folder(url: str) -> bool:
        """Check if url is a cda folder."""
        folder_regex1 = re.compile(
            r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
            (?!folder/)[a-z0-9_-]+)/?(\d*)""",
            re.VERBOSE | re.IGNORECASE,
        )
        folder_regex2 = re.compile(
            r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
            folder/\d+)/?(\d*)""",
            re.VERBOSE | re.IGNORECASE,
        )
        match = folder_regex1.match(url) or folder_regex2.match(url)
        return match is not None

    @staticmethod
    def get_adjusted_title(title: str) -> str:
        """Remove characters that are not allowed in the filename
        and convert spaces to underscores."""
        title = re.sub(r"[^\w\s-]", "", title)
        title = re.sub(r"[\s-]+", "_", title).strip("_")
        return title


class Video:
    video_id: str
    resolutions: list[str]
    video_soup: BeautifulSoup
    driver: webdriver.Chrome
    video_stream: requests.Response
    size: int
    title: str
    filepath: str

    def __init__(self, url: str, directory: str, resolution: str) -> None:
        self.url = url
        self.directory = directory
        self.resolution = resolution

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
        self.size = int(self.video_stream.headers.get("content-length", 0))
        self.title = self.get_title()
        self.filepath = self.get_filepath()

    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        video_regex = re.compile(
            r"""https?://(?:(?:www|ebd)\.)?cda\.pl/
            (?:video|[0-9]+x[0-9]+)/([0-9a-z]+)""",
            re.VERBOSE | re.IGNORECASE,
        )
        match = video_regex.match(self.url)
        assert match
        return match.group(1)

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
        src = video["src"]
        if not isinstance(src, str):
            exit("Error podczas parsowania 'video stream'")
        video_stream = requests.get(src, stream=True)
        return video_stream

    def get_size(self) -> int:
        """Get Video size in KiB."""
        return int(self.video_stream.headers.get("content-length", 0))

    def get_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            exit("Error podczas parsowania 'title'")
        title = title_tag.text.strip("\n")
        return Downloader.get_adjusted_title(title)

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


class Folder:
    title: str
    videos: list[Video]
    folders: list["Folder"]

    def __init__(self, url: str, directory: str) -> None:
        self.url = url
        self.url = self.get_adjusted_url()
        self.directory = directory

    def get_adjusted_url(self) -> str:
        """If the url has no page specified, add /1/ at the
        end of it, indicating that we start from the page 1."""
        if not self.url.endswith("/"):
            self.url += "/"
        folder_regex1 = re.compile(
            r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
            (?!folder/)[a-z0-9_-]+)/?(\d*)""",
            re.VERBOSE | re.IGNORECASE,
        )
        folder_regex2 = re.compile(
            r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
            folder/\d+)/?(\d*)""",
            re.VERBOSE | re.IGNORECASE,
        )
        match = folder_regex1.match(self.url) or folder_regex2.match(self.url)
        if match and match.group(2):
            return self.url
        else:
            return self.url + "1/"

    def download_folder(self) -> None:
        """Recursively download all videos and subfolders of the folder."""
        self.make_directory()
        self.folders = self.get_subfolders()
        if len(self.folders) > 0:
            self.download_subfolders()
        self.videos = self.get_videos_from_folder()
        if len(self.videos) > 0:
            self.download_videos_from_folder()

    def download_subfolders(self) -> None:
        """Download all subfolders of the folder."""
        for folder in tqdm(
            self.folders, total=len(self.folders), desc=self.title, leave=False
        ):
            folder.download_folder()

    def make_directory(self) -> None:
        """Make directory for the folder."""
        self.title = self.get_folder_title()
        self.directory = os.path.join(self.directory, self.title)
        Path(self.directory).mkdir(parents=True, exist_ok=True)

    def get_folder_title(self) -> str:
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")
        try:
            title_wrapper = soup.find_all("span", class_="folder-one-line")[-1]
        except IndexError:
            exit("Error podczas parsowania 'folder title'")
        title = title_wrapper.find("a", href=True).text
        return Downloader.get_adjusted_title(title)

    def get_subfolders(self) -> list["Folder"]:
        """Get subfolders of the folder."""
        response = requests.get(self.url)
        page_soup = BeautifulSoup(response.text, "html.parser")
        folders_soup = page_soup.find_all(
            "a", href=True, class_="object-folder"
        )
        folders = [
            Folder(folder["href"], self.directory)
            for folder in folders_soup
            if "data-foldery_id" in folder.attrs
        ]
        return folders

    def download_videos_from_folder(self) -> None:
        """Download all videos from the folder."""
        for video in tqdm(
            self.videos, total=len(self.videos), desc=self.title, leave=False
        ):
            video.download_video()

    def get_videos_from_folder(self) -> list[Video]:
        """Get all videos from the folder."""
        all_videos: list[Video] = []
        while True:
            videos = self.get_videos_from_current_page()
            if len(videos) == 0:
                break
            all_videos.extend(videos)
            self.url = self.get_next_page()
        return all_videos

    def get_videos_from_current_page(self) -> list[Video]:
        """Get all videos from the current page."""
        response = requests.get(self.url)
        page_soup = BeautifulSoup(response.content, "html.parser")
        videos_soup = page_soup.find_all(
            "a", href=True, class_="thumbnail-link"
        )
        videos = [
            Video(
                "https://www.cda.pl" + video["href"],
                self.directory,
                "najlepsza",
            )
            for video in videos_soup
        ]
        return videos

    def get_next_page(self) -> str:
        """Get next page of the folder."""
        folder_regex1 = re.compile(
            r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
            (?!folder/)[a-z0-9_-]+)/?(\d*)""",
            re.VERBOSE | re.IGNORECASE,
        )
        folder_regex2 = re.compile(
            r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
            folder/\d+)/?(\d*)""",
            re.VERBOSE | re.IGNORECASE,
        )
        match = folder_regex1.match(self.url) or folder_regex2.match(self.url)
        assert match
        page_number = int(match.group(2))
        stripped_url = match.group(1)
        return stripped_url + "/" + str(page_number + 1) + "/"


# TODO: organize this shit to different files
# TODO: write README.md in polish
# TODO: resume folder download if it was previously cancelled
# TODO: add async
# TODO: maybe support for premium videos on login?
