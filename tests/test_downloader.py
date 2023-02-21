import logging
import os
import sys
from typing import Any

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.downloader import Downloader
from cda_dl.main import parse_args
from cda_dl.utils import is_folder, is_video

LOGGER = logging.getLogger(__name__)


VIDEO_URLS = [
    "https://www.cda.pl/video/9122600a",
    "https://www.cda.pl/video/70460839/",
    "https://www.cda.pl/video/11051590f8/vfilm",
    "https://www.cda.pl/video/11051590f8/vfilm/",
    "https://ebd.cda.pl/1920x1080/9122600a",
    "https://ebd.cda.pl/1920x1080/9122600a/",
]

FOLDER_URLS = [
    "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349",
    "https://www.cda.pl/kreskowkatv/folder-glowny",
    "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/",
    "https://www.cda.pl/kreskowkatv/folder-glowny/",
    "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/10",
    "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/100/",
]


def test_is_video() -> None:
    for url in VIDEO_URLS:
        assert is_video(url) is True

    for url in FOLDER_URLS:
        assert is_video(url) is False


def test_is_folder() -> None:
    for url in VIDEO_URLS:
        assert is_folder(url) is False

    for url in FOLDER_URLS:
        assert is_folder(url) is True


def test_list_resolutions_and_exit_folder(caplog: Any) -> None:
    for url in FOLDER_URLS:
        args = parse_args(["-R", url])
        with pytest.raises(SystemExit, match=""):
            Downloader(args)
            assert (
                "Flaga -R jest dostępna tylko dla filmów."
                f" {url} jest folderem!"
                in caplog.text
            )


def test_list_resolutions_and_exit_video(caplog: Any) -> None:
    url = "https://www.cda.pl/video/9122600a"
    args = parse_args(["-R", url])
    with pytest.raises(SystemExit, match=""):
        Downloader(args)
        assert f"Dostępne rozdzielczości dla {url}:" in caplog.text


def test_list_resolutions_and_exit_unknown(caplog: Any) -> None:
    url = "https://www.google.com"
    args = parse_args(["-R", url])
    with pytest.raises(SystemExit, match=""):
        Downloader(args)
        assert f"Nie rozpoznano adresu url: {url}" in caplog.text


def test_handle_r_flag_folder(caplog: Any) -> None:
    for url in FOLDER_URLS:
        res = "720p"
        args = parse_args(["-r", res, url])
        Downloader(args)
        assert (
            f"Flaga -r jest dostępna tylko dla filmów. {url} jest folderem!"
            in caplog.text
        )


def test_handle_r_flag_video(caplog: Any) -> None:
    url = "https://www.cda.pl/video/9122600a"
    invalid_resolutions = ["144p", "360p", "720p"]
    for res in invalid_resolutions:
        args = parse_args(["-r", res, url])
        Downloader(args)
        assert (
            f"{res} rozdzielczość nie jest dostępna dla {url}" in caplog.text
        )


def test_handle_r_flag_unknown(caplog: Any) -> None:
    url = "https://www.google.com"
    res = "720p"
    args = parse_args(["-r", res, url])
    Downloader(args)
    assert f"Nie rozpoznano adresu url: {url}" in caplog.text
