import json
import os
import sys
from typing import TypedDict, cast

import pytest
from aiohttp import ClientSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.folder import Folder


class _Folder(TypedDict):
    url: str
    adjusted_url: str
    next_page_url: str
    title: str
    nsubfolders: int
    nvideos: int


class _Tests(TypedDict):
    folders: list[_Folder]


def get_test_data() -> list[_Folder]:
    folder_path = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(folder_path, "test_data.json")
    with open(json_file, "r") as f:
        dat: _Tests = json.load(f)
    return dat["folders"]


FOLDERS = get_test_data()


def test_get_adjusted_url() -> None:
    for folder in FOLDERS:
        # get_adjusted_url is called in the Folder constructor
        f = Folder(folder["url"], ".", cast(ClientSession, None))
        assert f.url == folder["adjusted_url"]


@pytest.mark.asyncio
async def test_get_folder_title() -> None:
    for folder in FOLDERS:
        async with ClientSession() as session:
            f = Folder(folder["url"], ".", session)
            f.soup = await f.get_soup()
            assert await f.get_folder_title() == folder["title"]


def test_get_next_page() -> None:
    for folder in FOLDERS:
        f = Folder(folder["url"], ".", cast(ClientSession, None))
        assert f.get_next_page() == folder["next_page_url"]


@pytest.mark.asyncio
async def test_get_videos_from_folder() -> None:
    for folder in FOLDERS:
        async with ClientSession() as session:
            f = Folder(folder["url"], ".", session)
            assert len(await f.get_videos_from_folder()) == folder["nvideos"]


@pytest.mark.asyncio
async def test_get_subfolders() -> None:
    for folder in FOLDERS:
        async with ClientSession() as session:
            f = Folder(folder["url"], ".", session)
            f.soup = await f.get_soup()
            assert len(await f.get_subfolders()) == folder["nsubfolders"]
