import json
import os
import sys
from asyncio import Semaphore
from typing import cast

import pytest
from aiohttp import ClientSession
from rich.table import Table

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.download_options import DownloadOptions
from cda_dl.download_state import DownloadState
from cda_dl.folder import Folder
from cda_dl.ui import RichUI

directory = os.path.abspath(os.path.dirname(__file__))
FOLDER_DATA = json.load(open(os.path.join(directory, "folder_data.json")))[
    "folders"
]


def test_get_adjusted_url() -> None:
    for folder in FOLDER_DATA:
        f = Folder(
            folder["url"], cast(ClientSession, None), cast(RichUI, None)
        )
        assert f.url == folder["adjusted_url"]


def test_get_next_page_url() -> None:
    for folder in FOLDER_DATA:
        f = Folder(
            folder["url"], cast(ClientSession, None), cast(RichUI, None)
        )
        assert f.get_next_page_url() == folder["next_page_url"]


@pytest.mark.asyncio
async def test_get_folder_title() -> None:
    for folder in FOLDER_DATA:
        if not folder["title"]:
            continue
        async with ClientSession() as session:
            f = Folder(folder["url"], session, cast(RichUI, None))
            f.soup = await f.get_soup()
            assert await f.get_folder_title() == folder["title"]


@pytest.mark.asyncio
async def test_get_videos_from_current_page() -> None:
    for folder in FOLDER_DATA:
        if folder["pagenvideos"] == -1:
            continue
        async with ClientSession() as session:
            f = Folder(folder["url"], session, cast(RichUI, None))
            f.soup = await f.get_soup()
            assert (
                len(await f.get_videos_from_current_page())
                == folder["pagenvideos"]
            )


@pytest.mark.asyncio
async def test_get_videos_from_folder() -> None:
    for folder in FOLDER_DATA:
        async with ClientSession() as session:
            f = Folder(folder["url"], session, cast(RichUI, None))
            assert len(await f.get_videos_from_folder()) == folder["nvideos"]


@pytest.mark.asyncio
async def test_get_subfolders() -> None:
    for folder in FOLDER_DATA:
        if folder["nsubfolders"] == -1:
            continue
        async with ClientSession() as session:
            f = Folder(folder["url"], session, cast(RichUI, None))
            f.soup = await f.get_soup()
            assert len(await f.get_subfolders()) == folder["nsubfolders"]


@pytest.mark.asyncio
async def test_download_folder() -> None:
    url = "https://www.cda.pl/ARAN_Inc-/folder/29375711"
    ui = RichUI(Table())
    ui.set_progress_bar_folder("")
    download_options = DownloadOptions(resolution="480p", overwrite=True)
    download_options.semaphore = Semaphore(download_options.nthreads)
    download_state = DownloadState()
    async with ClientSession() as session:
        f = Folder(url, session, ui)
        await f.download_folder(download_options, download_state)
        for v in f.videos:
            s = os.stat(v.filepath)
            assert s.st_size == v.remaining_size
