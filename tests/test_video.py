import os
import sys
from typing import Any, cast

import pytest
from aiohttp import ClientSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.error import GeoBlockedError, LoginRequiredError, ResolutionError
from cda_dl.video import Video


def test_get_videoid() -> None:
    url = "https://www.cda.pl/video/9122600a"
    videoid = "9122600a"
    v = Video(url, ".", "najlepsza", cast(ClientSession, None))
    assert v.get_videoid() == videoid


def test_get_videoid_slash() -> None:
    url = "https://www.cda.pl/video/9122600a/"
    videoid = "9122600a"
    v = Video(url, ".", "najlepsza", cast(ClientSession, None))
    assert v.get_videoid() == videoid


def test_get_videoid_ebd() -> None:
    url = "https://ebd.cda.pl/1920x1080/546614af"
    videoid = "546614af"
    v = Video(url, ".", "najlepsza", cast(ClientSession, None))
    assert v.get_videoid() == videoid


def test_get_videoid_ebd_slash() -> None:
    url = "https://ebd.cda.pl/1920x1080/546614af/"
    videoid = "546614af"
    v = Video(url, ".", "najlepsza", cast(ClientSession, None))
    assert v.get_videoid() == videoid


def test_get_videoid_premium_video() -> None:
    url = "https://www.cda.pl/video/11051590f8/vfilm"
    videoid = "11051590f8"
    v = Video(url, ".", "najlepsza", cast(ClientSession, None))
    assert v.get_videoid() == videoid


def test_get_videoid_premium_video_slash() -> None:
    url = "https://www.cda.pl/video/11051590f8/vfilm/"
    videoid = "11051590f8"
    v = Video(url, ".", "najlepsza", cast(ClientSession, None))
    assert v.get_videoid() == videoid


@pytest.mark.asyncio
async def test_premium_video() -> None:
    url = "https://www.cda.pl/video/63289011/vfilm"
    async with ClientSession() as session:
        v = Video(url, ".", "najlepsza", session)
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
        v = Video(url, ".", "najlepsza", session)
        with pytest.raises(
            GeoBlockedError,
            match="To wideo jest niedostępne w Twoim kraju. Pomijam ...",
        ):
            v.video_id = v.get_videoid()
            v.video_soup = await v.get_video_soup()
            v.check_geolocation()


@pytest.mark.asyncio
async def test_get_resolutions() -> None:
    url = "https://www.cda.pl/video/546614af"
    resolutions = ["360p", "480p", "720p"]
    async with ClientSession() as session:
        v = Video(url, ".", "najlepsza", session)
        v.video_id = v.get_videoid()
        v.video_soup = await v.get_video_soup()
        v.video_info = await v.get_video_info()
        assert await v.get_resolutions() == resolutions


@pytest.mark.asyncio
async def test_get_resolutions_ebd() -> None:
    url = "https://ebd.cda.pl/1920x1080/9122600a"
    resolutions = ["480p"]
    async with ClientSession() as session:
        v = Video(url, ".", "najlepsza", session)
        v.video_id = v.get_videoid()
        v.video_soup = await v.get_video_soup()
        v.video_info = await v.get_video_info()
        assert await v.get_resolutions() == resolutions


@pytest.mark.asyncio
async def test_get_adjusted_resolution() -> None:
    url = "https://www.cda.pl/video/546614af"
    adjusted_resolution = "720p"
    async with ClientSession() as session:
        v = Video(url, ".", "najlepsza", session)
        v.video_id = v.get_videoid()
        v.video_soup = await v.get_video_soup()
        v.video_info = await v.get_video_info()
        v.resolutions = await v.get_resolutions()
        assert v.get_adjusted_resolution() == adjusted_resolution


@pytest.mark.asyncio
async def test_check_resolution() -> None:
    url = "https://www.cda.pl/video/546614af"
    invalid_resolutions = ["144p", "1080p"]
    async with ClientSession() as session:
        v = Video(url, ".", "najlepsza", session)
        v.video_id = v.get_videoid()
        v.video_soup = await v.get_video_soup()
        v.video_info = await v.get_video_info()
        v.resolutions = await v.get_resolutions()
        for res in invalid_resolutions:
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
    url = "https://www.cda.pl/video/546614af"
    title = "Pokemon_Indigo_League_02_Ostry_dyżur_Pokemon"
    async with ClientSession() as session:
        v = Video(url, ".", "najlepsza", session)
        v.video_id = v.get_videoid()
        v.video_soup = await v.get_video_soup()
        assert v.get_video_title() == title


@pytest.mark.asyncio
async def test_get_video_title_ebd() -> None:
    url = "https://ebd.cda.pl/1920x1080/546614af"
    title = "Pokemon_Indigo_League_02_Ostry_dyżur_Pokemon"
    async with ClientSession() as session:
        v = Video(url, ".", "najlepsza", session)
        v.video_id = v.get_videoid()
        v.video_soup = await v.get_video_soup()
        assert v.get_video_title() == title


@pytest.mark.asyncio
async def test_download_video_overwrite() -> None:
    url = "https://www.cda.pl/video/7779552a9"
    async with ClientSession() as session:
        v = Video(url, ".", "480p", session)
        await v.download_video(overwrite=True)
        s = os.stat(v.filepath)
        assert s.st_size == v.size


@pytest.mark.asyncio
async def test_download_video(caplog: Any) -> None:
    url = "https://www.cda.pl/video/7779552a9"
    async with ClientSession() as session:
        v = Video(url, ".", "480p", session)
        await v.download_video(overwrite=False)
        assert f"Plik '{v.title}.mp4' już istnieje. Pomijam ..." in caplog.text
