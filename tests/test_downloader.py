import json
import os
import sys
from typing import TypedDict

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.downloader import Downloader
from cda_dl.main import parse_args
from cda_dl.utils import is_folder, is_video


class _Video(TypedDict):
    url: str
    videoid: str
    resolutions: list[str]
    adjusted_resolution: str
    invalid_resolutions: list[str]


class _Folder(TypedDict):
    url: str
    adjusted_url: str
    next_page_url: str
    title: str
    nsubfolders: int
    nvideos: int


class Unknown(TypedDict):
    url: str


class _Tests(TypedDict):
    videos: list[_Video]
    folders: list[_Folder]
    unknown: list[Unknown]


def get_test_data() -> _Tests:
    folder_path = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(folder_path, "test_data.json")
    with open(json_file, "r") as f:
        dat: _Tests = json.load(f)
    return dat


TEST_DATA = get_test_data()


def test_list_resolutions_and_exit_folder() -> None:
    for folder in TEST_DATA["folders"]:
        args = parse_args(["-R", folder["url"]])
        with pytest.raises(
            SystemExit,
            match=(
                "Flaga -R jest dostępna tylko dla filmów."
                f" {folder['url']} jest folderem!"
            ),
        ):
            Downloader(args)


def test_list_resolutions_and_exit_video() -> None:
    for video in TEST_DATA["videos"]:
        args = parse_args(["-R", video["url"]])
        with pytest.raises(SystemExit, match=""):
            Downloader(args)


def test_list_resolutions_and_exit_unknown() -> None:
    for unknown in TEST_DATA["unknown"]:
        args = parse_args(["-R", unknown["url"]])
        with pytest.raises(
            SystemExit, match=f"Nie rozpoznano adresu url: {unknown['url']}"
        ):
            Downloader(args)


def test_handle_r_flag_folder() -> None:
    for folder in TEST_DATA["folders"]:
        res = "720p"
        args = parse_args(["-r", res, folder["url"]])
        with pytest.raises(
            SystemExit,
            match=(
                "Flaga -r jest dostępna tylko dla filmów."
                f" {folder['url']} jest folderem!"
            ),
        ):
            Downloader(args)


def test_handle_r_flag_video() -> None:
    # Slice cause too many requests
    for video in TEST_DATA["videos"][:2]:
        for res in video["invalid_resolutions"]:
            args = parse_args(["-r", res, video["url"]])
            with pytest.raises(
                SystemExit,
                match=(
                    f"{res} rozdzielczość nie jest dostępna dla {video['url']}"
                ),
            ):
                Downloader(args)


def test_handle_r_flag_unknown() -> None:
    for unknown in TEST_DATA["unknown"]:
        res = "720p"
        args = parse_args(["-r", res, unknown["url"]])
        with pytest.raises(
            SystemExit, match=f"Nie rozpoznano adresu url: {unknown['url']}"
        ):
            Downloader(args)


def test_is_video() -> None:
    for video in TEST_DATA["videos"]:
        assert is_video(video["url"]) is True

    for folder in TEST_DATA["folders"]:
        assert is_video(folder["url"]) is False

    for unknown in TEST_DATA["unknown"]:
        assert is_video(unknown["url"]) is False


def test_is_folder() -> None:
    for video in TEST_DATA["videos"]:
        assert is_folder(video["url"]) is False

    for folder in TEST_DATA["folders"]:
        assert is_folder(folder["url"]) is True

    for unknown in TEST_DATA["unknown"]:
        assert is_folder(unknown["url"]) is False
