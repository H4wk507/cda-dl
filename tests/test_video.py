import sys
import os
import pytest
from typing import TypedDict
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_downloader.main import Video


class _Video(TypedDict):
    url: str
    videoid: str
    resolutions: list[str]
    adjusted_resolution: str
    invalid_resolutions: list[str]


class _Tests(TypedDict):
    videos: list[_Video]


def get_test_data() -> list[_Video]:
    folder_path = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(folder_path, "test_data.json")
    with open(json_file, "r") as f:
        dat: _Tests = json.load(f)
    return dat["videos"]


VIDEOS = get_test_data()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
}

def test_get_videoid() -> None:
    for video in VIDEOS:
        v = Video(video["url"], ".", "najlepsza", HEADERS)
        assert v.get_videoid() == video["videoid"]


def test_get_resolutions() -> None:
    for video in VIDEOS:
        v = Video(video["url"], ".", "najlepsza", HEADERS)
        v.video_id = v.get_videoid()
        assert v.get_resolutions() == video["resolutions"]


def test_get_adjusted_resolution() -> None:
    for video in VIDEOS:
        v = Video(video["url"], ".", "najlepsza", HEADERS)
        v.video_id = v.get_videoid()
        v.resolutions = v.get_resolutions()
        assert v.get_adjusted_resolution() == video["adjusted_resolution"]


def test_check_resolution() -> None:
    # Slice cause too many requests
    for video in VIDEOS[:2]:
        v = Video(video["url"], ".", "najlepsza", HEADERS)
        v.video_id = v.get_videoid()
        v.resolutions = v.get_resolutions()
        for res in video["invalid_resolutions"]:
            v.resolution = res
            with pytest.raises(
                SystemExit,
                match=(
                    f"{v.resolution} rozdzielczość nie jest dostępna dla"
                    f" {v.url}"
                ),
            ):
                v.check_resolution()
