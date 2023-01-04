import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from ..main import Video
import pytest  # type: ignore
from selenium import webdriver
from typing import cast


def test_get_videoid() -> None:
    url = "https://www.cda.pl/video/9122600a"
    videoid = "9122600a"
    v = Video(url, ".", "best", cast(webdriver.Chrome, None))
    assert v.get_videoid() == videoid


def test_get_resolutions() -> None:
    url = "https://www.cda.pl/video/9122600a"
    resolutions = ["480p"]
    v = Video(url, ".", "best", cast(webdriver.Chrome, None))
    assert v.get_resolutions() == resolutions


def test_get_adjusted_resolution() -> None:
    url = "https://www.cda.pl/video/9122600a"
    best_resolution = "480p"
    v = Video(url, ".", "best", cast(webdriver.Chrome, None))
    v.resolutions = v.get_resolutions()
    assert v.get_adjusted_resolution() == best_resolution


def test_check_resolution() -> None:
    url = "https://www.cda.pl/video/9122600a"
    v = Video(url, ".", "best", cast(webdriver.Chrome, None))
    v.resolution = "120p"
    v.resolutions = v.get_resolutions()
    with pytest.raises(
        SystemExit,
        match=f"{v.resolution} resolution is not available for {url}",
    ):
        v.check_resolution()


def test_get_video_stream() -> None:
    pass


def test_get_title() -> None:
    pass


def test_get_adjusted_title() -> None:
    pass


def test_get_filepath() -> None:
    pass


def test_stream_data() -> None:
    pass


# Don't test downloading the video, too long
