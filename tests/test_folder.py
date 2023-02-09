import sys
import os
import json
from selenium import webdriver
from typing import cast, TypedDict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_downloader.main import Folder


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


def test_get_adjusted_url() -> None:
    for folder in FOLDERS:
        # get_adjusted_url is called in the Folder constructor
        f = Folder(folder["url"], ".", cast(webdriver.Chrome, None))
        assert f.url == folder["adjusted_url"]


def test_get_folder_title() -> None:
    # last 3 folders are incorrect so we can't get title out of them
    for folder in FOLDERS[:-3]:
        f = Folder(folder["url"], ".", cast(webdriver.Chrome, None))
        assert f.get_folder_title() == folder["title"]


def test_get_next_page() -> None:
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", cast(webdriver.Chrome, None))
        assert f.get_next_page() == folder["next_page_url"]


def test_get_videos_from_folder() -> None:
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", cast(webdriver.Chrome, None))
        assert len(f.get_videos_from_folder()) == folder["nvideos"]


from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService


def get_webdriver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=ChromeService(
            ChromeDriverManager(cache_valid_range=1).install()
        ),
        options=options,
    )
    return driver


def test_get_subfolders() -> None:
    driver = get_webdriver()
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", driver)
        assert len(f.get_subfolders()) == folder["nsubfolders"]
