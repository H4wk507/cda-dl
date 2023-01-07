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


class _Tests(TypedDict):
    folders: list[_Folder]


def get_test_data() -> list[_Folder]:
    folder_path = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(folder_path, "test_data.json")
    with open(json_file) as f:
        dat: _Tests = json.load(f)
    return dat["folders"]


FOLDERS = get_test_data()


def test_get_adjusted_url() -> None:
    for folder in FOLDERS:
        # get_adjusted_url is called in the Folder constructor
        f = Folder(folder["url"], ".", cast(webdriver.Chrome, None))
        assert f.url == folder["adjusted_url"]


def test_get_next_page() -> None:
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", cast(webdriver.Chrome, None))
        assert f.get_next_page() == folder["next_page_url"]
