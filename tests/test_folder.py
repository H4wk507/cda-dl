import os
import sys
from asyncio import Semaphore
from typing import cast

import pytest
from aiohttp import ClientSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.folder import Folder


def test_get_adjusted_url_no_page() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349"
    adjusted_url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/1/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_adjusted_url_no_page2() -> None:
    url = "https://www.cda.pl/kreskowkatv/folder-glowny"
    adjusted_url = "https://www.cda.pl/kreskowkatv/folder-glowny/1/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_adjusted_url_no_page_slash() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/"
    adjusted_url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/1/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_adjusted_url_no_page_slash2() -> None:
    url = "https://www.cda.pl/kreskowkatv/folder-glowny/"
    adjusted_url = "https://www.cda.pl/kreskowkatv/folder-glowny/1/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_adjusted_url_with_page() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/10"
    adjusted_url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/10/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_adjusted_url_no_with_page2() -> None:
    url = "https://www.cda.pl/kreskowkatv/folder-glowny/10"
    adjusted_url = "https://www.cda.pl/kreskowkatv/folder-glowny/10/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_adjusted_url_with_page_slash() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/100/"
    adjusted_url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/100/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_adjusted_url_with_page_slash2() -> None:
    url = "https://www.cda.pl/kreskowkatv/folder-glowny/100/"
    adjusted_url = "https://www.cda.pl/kreskowkatv/folder-glowny/100/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.url == adjusted_url


def test_get_next_page_url() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/10/"
    next_page_url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349/11/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.get_next_page_url() == next_page_url


def test_get_next_page_url2() -> None:
    url = "https://www.cda.pl/kreskowkatv/folder-glowny/10/"
    next_page_url = "https://www.cda.pl/kreskowkatv/folder-glowny/11/"
    f = Folder(url, ".", cast(ClientSession, None))
    assert f.get_next_page_url() == next_page_url


@pytest.mark.asyncio
async def test_get_folder_title() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
    title = "Pokemon_Indigo_League_Sezon_1"
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert await f.get_folder_title() == title


@pytest.mark.asyncio
async def test_get_folder_title2() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1178343"
    title = "Folder_główny"
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert await f.get_folder_title() == title


@pytest.mark.asyncio
async def test_get_folder_title3() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder-glowny"
    title = "Folder_główny"
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert await f.get_folder_title() == title


@pytest.mark.asyncio
async def test_get_videos_from_current_page() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/2397349"
    nvideos = 20
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert len(await f.get_videos_from_current_page()) == nvideos


@pytest.mark.asyncio
async def test_get_videos_from_current_page2() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1178343"
    nvideos = 1
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert len(await f.get_videos_from_current_page()) == nvideos


@pytest.mark.asyncio
async def test_get_videos_from_current_page3() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder-glowny"
    nvideos = 1
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert len(await f.get_videos_from_current_page()) == nvideos


@pytest.mark.asyncio
async def test_get_videos_from_folder() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
    nvideos = 85
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        assert len(await f.get_videos_from_folder()) == nvideos


@pytest.mark.asyncio
async def test_get_videos_from_folder2() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1178343"
    nvideos = 1
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        assert len(await f.get_videos_from_folder()) == nvideos


@pytest.mark.asyncio
async def test_get_videos_from_folder3() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder-glowny"
    nvideos = 1
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        assert len(await f.get_videos_from_folder()) == nvideos


@pytest.mark.asyncio
async def test_get_subfolders() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1178343"
    nsubfolders = 25
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert len(await f.get_subfolders()) == nsubfolders


@pytest.mark.asyncio
async def test_get_subfolders2() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder-glowny"
    nsubfolders = 25
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert len(await f.get_subfolders()) == nsubfolders


@pytest.mark.asyncio
async def test_get_subfolders3() -> None:
    url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
    nsubfolders = 0
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        f.soup = await f.get_soup()
        assert len(await f.get_subfolders()) == nsubfolders


@pytest.mark.asyncio
async def test_download_folder() -> None:
    url = "https://www.cda.pl/ARAN_Inc-/folder/29375711"
    async with ClientSession() as session:
        f = Folder(url, ".", session)
        await f.download_folder(Semaphore(3), overwrite=True)
        for v in f.videos:
            s = os.stat(v.filepath)
            assert s.st_size == v.size
