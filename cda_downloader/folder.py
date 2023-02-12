from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
from cda_downloader.video import Video
from cda_downloader.utils import get_adjusted_title, get_folder_match


class Folder:
    title: str
    videos: list[Video]
    folders: list["Folder"]

    def __init__(
        self, url: str, directory: str, headers: dict[str, str]
    ) -> None:
        self.url = url
        self.url = self.get_adjusted_url()
        self.directory = directory
        self.headers = headers

    def get_adjusted_url(self) -> str:
        """If the url has no page specified, add /1/ at the
        end of it, indicating that we start from the page 1."""
        if not self.url.endswith("/"):
            self.url += "/"
        match = get_folder_match(self.url)
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
        response = requests.get(self.url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        try:
            title_wrapper = soup.find_all("span", class_="folder-one-line")[-1]
        except IndexError:
            exit("Error podczas parsowania 'folder title'")
        title = title_wrapper.find("a", href=True).text
        return get_adjusted_title(title)

    def get_subfolders(self) -> list["Folder"]:
        """Get subfolders of the folder."""
        response = requests.get(self.url, headers=self.headers)
        page_soup = BeautifulSoup(response.text, "html.parser")
        folders_soup = page_soup.find_all(
            "a", href=True, class_="object-folder"
        )
        folders = [
            Folder(folder["href"], self.directory, self.headers)
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
        response = requests.get(self.url, headers=self.headers)
        page_soup = BeautifulSoup(response.content, "html.parser")
        videos_soup = page_soup.find_all(
            "a", href=True, class_="thumbnail-link"
        )
        videos = [
            Video(
                "https://www.cda.pl" + video["href"],
                self.directory,
                "najlepsza",
                self.headers,
            )
            for video in videos_soup
        ]
        return videos

    def get_next_page(self) -> str:
        """Get next page of the folder."""
        match = get_folder_match(self.url)
        assert match
        page_number = int(match.group(2))
        stripped_url = match.group(1)
        return stripped_url + "/" + str(page_number + 1) + "/"
