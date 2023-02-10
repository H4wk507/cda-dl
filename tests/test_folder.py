import sys
import os
import json
from typing import TypedDict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_downloader.folder import Folder


class _Folder(TypedDict):
    url: str
    adjusted_url: str
    next_page_url: str
    title: str
    nsubfolders: int
    nvideos: int


class _Tests(TypedDict):
    folders: list[_Folder]


def get_test_data() -> list[_Folder]:
    folder_path = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(folder_path, "test_data.json")
    with open(json_file, "r") as f:
        dat: _Tests = json.load(f)
    return dat["folders"]


FOLDERS = get_test_data()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
}


def test_get_adjusted_url() -> None:
    for folder in FOLDERS:
        # get_adjusted_url is called in the Folder constructor
        f = Folder(folder["url"], ".", HEADERS)
        assert f.url == folder["adjusted_url"]


def test_get_folder_title() -> None:
    # last 3 folders are incorrect so we can't get title out of them
    for folder in FOLDERS[:-3]:
        f = Folder(folder["url"], ".", HEADERS)
        assert f.get_folder_title() == folder["title"]


def test_get_next_page() -> None:
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", HEADERS)
        assert f.get_next_page() == folder["next_page_url"]


def test_get_videos_from_folder() -> None:
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", HEADERS)
        assert len(f.get_videos_from_folder()) == folder["nvideos"]


def test_get_subfolders() -> None:
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", HEADERS)
        assert len(f.get_subfolders()) == folder["nsubfolders"], folder["url"]
