import os
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from aiohttp import ClientSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from cda_dl.error import GeoBlockedError, LoginRequiredError, ResolutionError
from cda_dl.video import Video

directory = os.path.abspath(os.path.dirname(__file__))
VIDEO_DATA = json.load(open(os.path.join(directory, "video_data.json"), "r"))[
    "videos"
]


def test_get_videoid() -> None:
    for video in VIDEO_DATA:
        v = Video(
            video["url"], Path("."), "najlepsza", cast(ClientSession, None)
        )
        assert v.get_videoid() == video["videoid"]


@pytest.mark.asyncio
async def test_premium_video() -> None:
    url = "https://www.cda.pl/video/63289011/vfilm"
    async with ClientSession() as session:
        v = Video(url, Path("."), "najlepsza", session)
        with pytest.raises(
            LoginRequiredError,
            match=(
                "Ten film jest dostępny tylko dla użytkowników premium."
                " Pomijam ..."
            ),
        ):
            v.video_id = v.get_videoid()
            v.video_soup = await v.get_video_soup()
            v.check_premium()


@pytest.mark.asyncio
async def test_geoblocked() -> None:
    url = "https://www.cda.pl/video/124097194d/vfilm"
    async with ClientSession() as session:
        v = Video(url, Path("."), "najlepsza", session)
        with pytest.raises(
            GeoBlockedError,
            match="To wideo jest niedostępne w Twoim kraju. Pomijam ...",
        ):
            v.video_id = v.get_videoid()
            v.video_soup = await v.get_video_soup()
            v.check_geolocation()


@pytest.mark.asyncio
async def test_get_resolutions() -> None:
    for video in VIDEO_DATA:
        if not video["resolutions"]:
            continue
        async with ClientSession() as session:
            v = Video(video["url"], Path("."), "najlepsza", session)
            v.video_id = v.get_videoid()
            v.video_soup = await v.get_video_soup()
            v.video_info = await v.get_video_info()
            assert await v.get_resolutions() == video["resolutions"]


@pytest.mark.asyncio
async def test_get_adjusted_resolution() -> None:
    for video in VIDEO_DATA:
        if not video["adjusted_resolution"]:
            continue
        async with ClientSession() as session:
            v = Video(video["url"], Path("."), "najlepsza", session)
            v.video_id = v.get_videoid()
            v.video_soup = await v.get_video_soup()
            v.video_info = await v.get_video_info()
            v.resolutions = await v.get_resolutions()
            assert v.get_adjusted_resolution() == video["adjusted_resolution"]


@pytest.mark.asyncio
async def test_check_resolution() -> None:
    for video in VIDEO_DATA:
        if not video["invalid_resolutions"]:
            continue
        async with ClientSession() as session:
            v = Video(video["url"], Path("."), "najlepsza", session)
            v.video_id = v.get_videoid()
            v.video_soup = await v.get_video_soup()
            v.video_info = await v.get_video_info()
            v.resolutions = await v.get_resolutions()
            for res in video["invalid_resolutions"]:
                v.resolution = res
                with pytest.raises(
                    ResolutionError,
                    match=(
                        f"{v.resolution} rozdzielczość nie jest dostępna dla"
                        f" {v.url}"
                    ),
                ):
                    v.check_resolution()


@pytest.mark.asyncio
async def test_get_video_title() -> None:
    for video in VIDEO_DATA:
        async with ClientSession() as session:
            v = Video(video["url"], Path("."), "najlepsza", session)
            v.video_id = v.get_videoid()
            v.video_soup = await v.get_video_soup()
            assert v.get_video_title() == video["title"]


@pytest.mark.asyncio
async def test_download_video_overwrite() -> None:
    url = "https://www.cda.pl/video/7779552a9"
    async with ClientSession() as session:
        v = Video(url, Path("."), "480p", session)
        await v.download_video(overwrite=True)
        s = os.stat(v.filepath)
        assert s.st_size == v.remaining_size


@pytest.mark.asyncio
async def test_download_video_no_overwrite(caplog: Any) -> None:
    url = "https://www.cda.pl/video/7779552a9"
    async with ClientSession() as session:
        v = Video(url, Path("."), "480p", session)
        await v.download_video(overwrite=False)
        assert f"Plik '{v.title}.mp4' już istnieje. Pomijam ..." in caplog.text
