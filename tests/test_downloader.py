import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from ..__main__ import parse_args
from ..main import Downloader
import pytest  # type: ignore


def test_list_resolutions_and_exit_folder() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
    args = parse_args(["-R", url])
    with pytest.raises(
        SystemExit, match="-R flag is only available for videos."
    ):
        Downloader(args)


def test_list_resolutions_and_exit_video() -> None:
    url = "https://www.cda.pl/video/9122600a"
    args = parse_args(["-R", url])
    with pytest.raises(SystemExit, match=""):
        Downloader(args)


def test_list_resolutions_and_exit_unknown() -> None:
    url = "https://www.google.com"
    args = parse_args(["-R", url])
    with pytest.raises(
        SystemExit, match="Could not recognize the url. Aborting..."
    ):
        Downloader(args)


def test_handle_r_flag_folder() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
    res = "720p"
    args = parse_args(["-r", res, url])
    with pytest.raises(
        SystemExit, match="-r flag is only available for videos."
    ):
        Downloader(args)


def test_handle_r_flag_video() -> None:
    url = "https://www.cda.pl/video/9122600a"
    res = "720p"
    args = parse_args(["-r", res, url])
    with pytest.raises(
        SystemExit, match=f"{res} resolution is not available for {url}"
    ):
        Downloader(args)


def test_handle_r_flag_unknown() -> None:
    url = "https://www.google.com"
    res = "720p"
    args = parse_args(["-r", res, url])
    with pytest.raises(
        SystemExit, match="Could not recognize the url. Aborting..."
    ):
        Downloader(args)
