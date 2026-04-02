import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import shutil
from urllib.parse import urljoin

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag
from rich.console import Console
from rich.logging import RichHandler

from cda_dl.download_options import DownloadOptions
from cda_dl.download_state import DownloadState
from cda_dl.error import (
    GeoBlockedError,
    HTTPError,
    LoginRequiredError,
    ParserError,
    ResolutionError,
)
from cda_dl.ui import RichUI
from cda_dl.utils import (
    decrypt_url,
    get_request,
    get_safe_title,
    get_video_match,
    post_request,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False)],
)
LOGGER = logging.getLogger(__name__)


class Video:
    video_id: str
    resolutions: dict[str, str]
    video_soup: BeautifulSoup
    video_info: Any
    resolution: str
    file: str
    video_stream: aiohttp.ClientResponse
    remaining_size: int
    title: str
    filepath: Path
    partial_filepath: Path
    resume_point: int
    is_dash: bool
    dash_video_url: str
    dash_audio_url: str

    def __init__(
        self, url: str, session: aiohttp.ClientSession, ui: RichUI
    ) -> None:
        self.url = url
        self.session = session
        self.ui = ui
        self.headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.is_dash = False
        self.dash_video_url = ""
        self.dash_audio_url = ""

    def is_mpd_url(self, url: str) -> bool:
        return url.lower().endswith(".mpd")

    async def initialize_dash(self) -> None:
        response = await get_request(self.file, self.session, {})
        mpd_text = await response.text()
        self.dash_video_url, self.dash_audio_url = self.parse_mpd(
            mpd_text, self.file
        )

    def parse_mpd(self, mpd_text: str, mpd_url: str) -> tuple[str, str]:
        soup = BeautifulSoup(mpd_text, "xml")

        video_url = None
        audio_url = None

        for adaptation_set in soup.find_all("AdaptationSet"):
            content_type = adaptation_set.get("contentType")

            if content_type == "video":
                matched_representation = None

                for representation in adaptation_set.find_all("Representation"):
                    height = representation.get("height")
                    if height and self.resolution == f"{height}p":
                        matched_representation = representation
                        break

                if matched_representation is None:
                    representations = adaptation_set.find_all("Representation")
                    if not representations:
                        continue
                    matched_representation = max(
                        representations,
                        key=lambda rep: int(rep.get("height", "0")),
                    )

                base_url = matched_representation.find("BaseURL")
                if base_url and base_url.text:
                    video_url = urljoin(mpd_url, base_url.text.strip())

            elif content_type == "audio":
                representation = adaptation_set.find("Representation")
                if representation:
                    base_url = representation.find("BaseURL")
                    if base_url and base_url.text:
                        audio_url = urljoin(mpd_url, base_url.text.strip())

        if not video_url:
            raise ParserError(
                f"Nie udało się znaleźć strumienia video w MPD dla {self.url}"
            )

        if not audio_url:
            raise ParserError(
                f"Nie udało się znaleźć strumienia audio w MPD dla {self.url}"
            )

        return video_url, audio_url

    def get_dash_video_filepath(self) -> Path:
        return self.filepath.parent / f"{self.filepath.stem}.video.mp4"

    def get_dash_audio_filepath(self) -> Path:
        return self.filepath.parent / f"{self.filepath.stem}.audio.mp4"

    async def download_url_to_file(
        self, url: str, path: Path, desc: str
    ) -> None:
        response = await get_request(url, self.session, {})
        total = int(response.headers.get("content-length", 0))

        assert self.ui.progbar_video
        task_id = self.ui.progbar_video.add_task(
            "download",
            filename=desc,
            total=total if total > 0 else None,
        )

        async with aiofiles.open(path, "wb") as f:
            async for chunk in response.content.iter_chunked(1024 * 1024):
                await f.write(chunk)
                self.ui.progbar_video.update(task_id, advance=len(chunk))

        self.ui.progbar_video.remove_task(task_id)

    async def merge_dash_streams(
        self, video_path: Path, audio_path: Path, output_path: Path
    ) -> None:
        if shutil.which("ffmpeg") is None:
            raise ParserError(
                "Wykryto materiał MPEG-DASH, ale ffmpeg nie jest zainstalowany."
            )

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c",
            "copy",
            str(output_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return_code = await process.wait()

        if return_code != 0:
            raise ParserError(
                f"ffmpeg nie zdołał scalić audio i video dla {self.url}"
            )

    async def download_dash(self, download_state: DownloadState) -> None:
        video_tmp = self.get_dash_video_filepath()
        audio_tmp = self.get_dash_audio_filepath()

        self.filepath.unlink(missing_ok=True)
        video_tmp.unlink(missing_ok=True)
        audio_tmp.unlink(missing_ok=True)

        try:
            await self.download_url_to_file(
                self.dash_video_url,
                video_tmp,
                f"{self.title}.video.mp4 [{self.resolution}]",
            )
            await self.download_url_to_file(
                self.dash_audio_url,
                audio_tmp,
                f"{self.title}.audio.mp4 [{self.resolution}]",
            )
            await self.merge_dash_streams(video_tmp, audio_tmp, self.filepath)
        finally:
            video_tmp.unlink(missing_ok=True)
            audio_tmp.unlink(missing_ok=True)

        download_state.completed += 1

    async def download_video(
        self, download_options: DownloadOptions, download_state: DownloadState
    ) -> None:
        LOGGER.level = (
            logging.WARNING if download_options.quiet else logging.INFO
        )
        try:
            await self.pre_initialize(download_options)
            if self.filepath.exists() and not download_options.overwrite:
                LOGGER.info(
                    f"Plik '{self.title}.mp4' już istnieje. Pomijam ..."
                )
                download_state.skipped += 1
                return
            await self.initialize(download_options)
        except (
            LoginRequiredError,
            GeoBlockedError,
            ResolutionError,
            ParserError,
            HTTPError,
        ) as e:
            if isinstance(e, HTTPError) and e.status_code == 429:
                LOGGER.warning("Zbyt dużo zapytań. Usypiam wątek na 10 min.")
                await asyncio.sleep(60 * 10)
                await self.download_video(download_options, download_state)
            else:
                LOGGER.warning(e)
                download_state.failed += 1
        else:
            self.make_directory(download_options)
            if self.is_dash:
                await self.download_dash(download_state)
            else:
                await self.stream_file(download_state)

    async def pre_initialize(self, download_options: DownloadOptions) -> None:
        """Initialize members required to get Video info."""
        self.video_soup = await self.get_video_soup()
        self.title = self.get_video_title()
        self.filepath = self.get_filepath(download_options)

    async def initialize(self, download_options: DownloadOptions) -> None:
        """Initialize members required to download the Video."""
        self.video_id = self.get_videoid()
        self.check_geolocation()
        self.partial_filepath = self.get_partial_filepath()
        self.check_premium()
        self.video_info = await self.get_video_info()
        self.resolutions = self.get_resolutions()
        self.resolution = self.get_adjusted_resolution(download_options)
        self.raise_invalid_res()
        cda_res = self.resolutions[self.resolution]
        resp = await post_request(
            self.url,
            self.session,
            {
                "id": 3,
                "jsonrpc": "2.0",
                "method": "videoGetLink",
                "params": [
                    self.video_id,
                    cda_res,
                    self.video_info["ts"],
                    self.video_info["hash2"],
                    {},
                ],
            },
            self.headers,
        )
        data = await resp.json()
        file_resp = data.get("result", {}).get("resp")

        if not isinstance(file_resp, str) or not file_resp.startswith(("http://", "https://")):
            raise ParserError(
                f"CDA nie zwróciło poprawnego linku do pliku dla {self.url}. "
                f"Odpowiedź API: {file_resp!r}"
            )

        self.file = file_resp
        self.resume_point = self.get_resume_point()

        if self.is_mpd_url(self.file):
            self.is_dash = True
            await self.initialize_dash()
        else:
            self.video_stream = await self.get_video_stream()
            self.remaining_size = self.get_remaining_size()


    def get_videoid(self) -> str:
        """Get videoid from Video url."""
        match = get_video_match(self.url)
        assert match
        return match.group(1)

    async def get_video_soup(self) -> BeautifulSoup:
        response = await get_request(self.url, self.session, self.headers)
        text = await response.text()
        return BeautifulSoup(text, "html.parser")

    def get_video_title(self) -> str:
        title_tag = self.video_soup.find("h1")
        if not isinstance(title_tag, Tag):
            raise ParserError(
                "Error podczas parsowania 'video title' dla"
                f" {self.url} Pomijam ..."
            )
        title = title_tag.text.strip("\n")
        return get_safe_title(title)

    def get_filepath(self, download_options: DownloadOptions) -> Path:
        return Path(download_options.directory, f"{self.title}.mp4")

    def get_partial_filepath(self) -> Path:
        return self.filepath.parent / f"{self.filepath.name}.part"

    def check_premium(self) -> None:
        if (
            "Ten film jest dostępny dla użytkowników premium"
            in self.video_soup.text
        ):
            raise LoginRequiredError(
                f"{self.title} jest dostępny tylko dla użytkowników premium."
                " Pomijam ..."
            )

    def check_geolocation(self) -> None:
        if re.search(
            r"niedostępn[ey] w(?:&nbsp;|\s+)Twoim kraju\s*",
            self.video_soup.text,
        ):
            raise GeoBlockedError(
                f"{self.url} jest niedostępny w Twoim kraju. Pomijam ..."
            )

    async def get_video_info(self) -> Any:
        """Get Video info from the url."""
        media_player = self.video_soup.find(
            "div", {"id": f"mediaplayer{self.video_id}"}
        )
        if not isinstance(media_player, Tag):
            raise ParserError(
                f"Error podczas parsowania 'media player' dla {self.title}."
                " Pomijam ..."
            )
        player_data = json.loads(media_player.attrs["player_data"])
        return player_data["video"]

    def get_resolutions(self) -> dict[str, str]:
        """Get available Video resolutions at the url."""
        return self.video_info["qualities"]  # type: ignore

    async def list_resolutions(self) -> None:
        self.video_id = self.get_videoid()
        self.video_soup = await self.get_video_soup()
        self.video_info = await self.get_video_info()
        resolutions = self.get_resolutions()
        console = Console()
        console.print(f"Dostępne rozdzielczości dla {self.url}")
        for res in resolutions:
            console.print(res)

    async def check_resolution(
        self, download_options: DownloadOptions
    ) -> None:
        self.video_id = self.get_videoid()
        self.video_soup = await self.get_video_soup()
        self.video_info = await self.get_video_info()
        self.resolutions = self.get_resolutions()
        self.resolution = download_options.resolution
        self.raise_invalid_res()

    def get_best_resolution(self) -> str:
        """Get best Video resolution available at the url."""
        numeric_resolutions = []
        for k in self.resolutions.keys():
            # Skip non-numeric resolution keys like 'aut'
            if k.endswith('p') and k[:-1].isdigit():
                numeric_resolutions.append(int(k[:-1]))
        
        if not numeric_resolutions:
            # If no numeric resolutions found, return the first available resolution
            return list(self.resolutions.keys())[0]
            
        return f"{max(numeric_resolutions)}p"

    def is_valid_resolution(self) -> bool:
        return self.resolution in self.resolutions

    def get_adjusted_resolution(
        self, download_options: DownloadOptions
    ) -> str:
        return (
            self.get_best_resolution()
            if download_options.resolution == "najlepsza"
            else download_options.resolution
        )

    def raise_invalid_res(self) -> None:
        """Raise ResolutionError if resolution is invalid."""
        if not self.is_valid_resolution():
            raise ResolutionError(
                f"{self.resolution} rozdzielczość nie jest dostępna dla"
                f" {self.url}"
            )

    def get_file(self) -> str:
        """Get decrypted link to the file download."""
        return decrypt_url(self.video_info["file"])

    def get_resume_point(self) -> int:
        return (
            self.partial_filepath.stat().st_size
            if self.partial_filepath.exists()
            else 0
        )

    async def get_video_stream(self) -> aiohttp.ClientResponse:
        if not isinstance(self.file, str) or not self.file.startswith(("http://", "https://")):
            raise ParserError(f"Nieprawidłowy URL strumienia: {self.file!r}")

        headers = {"Range": f"bytes={self.resume_point}-"}
        video_stream = await get_request(self.file, self.session, headers)
        return video_stream

    def get_remaining_size(self) -> int:
        """Get remaining Video size in KiB."""
        return int(self.video_stream.headers.get("content-length", 0))

    def make_directory(self, download_options: DownloadOptions) -> None:
        download_options.directory.mkdir(parents=True, exist_ok=True)

    async def stream_file(self, download_state: DownloadState) -> None:
        block_size = 1024
        desc = f"{self.title}.mp4 [{self.resolution}]"
        self.filepath.unlink(missing_ok=True)
        assert self.ui.progbar_video
        task_id = self.ui.progbar_video.add_task(
            "download",
            filename=desc,
            total=self.resume_point + self.remaining_size,
            completed=self.resume_point,
        )
        async with aiofiles.open(self.partial_filepath, "ab") as f:
            async for chunk in self.video_stream.content.iter_chunked(
                block_size * block_size
            ):
                await f.write(chunk)
                self.ui.progbar_video.update(task_id, advance=len(chunk))
        self.partial_filepath.rename(self.filepath)
        self.ui.progbar_video.remove_task(task_id)
        download_state.completed += 1
