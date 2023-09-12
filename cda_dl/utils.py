import os
import random
import re
import urllib.parse

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_fixed,
)

from cda_dl.error import HTTPError


def get_video_match(url: str) -> re.Match[str] | None:
    video_regex = re.compile(
        r"""https?://(?:(?:www|ebd)\.)?cda\.pl/
        (?:video|[0-9]+x[0-9]+)/([0-9a-z]+)""",
        re.VERBOSE | re.IGNORECASE,
    )
    return video_regex.match(url)


def is_video(url: str) -> bool:
    """Check if url is a cda video."""
    match = get_video_match(url)
    return match is not None


def get_folder_match(url: str) -> re.Match[str] | None:
    folder_regex1 = re.compile(
        r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
        (?!folder/)[a-z0-9_-]+)/?(\d*)""",
        re.VERBOSE | re.IGNORECASE,
    )
    folder_regex2 = re.compile(
        r"""(https?://(?:www\.)?cda\.pl/(?!video)[a-z0-9_-]+/
        folder/\d+)/?(\d*)""",
        re.VERBOSE | re.IGNORECASE,
    )
    return folder_regex1.match(url) or folder_regex2.match(url)


def is_folder(url: str) -> bool:
    """Check if url is a cda folder."""
    match = get_folder_match(url)
    return match is not None


def get_safe_title(title: str) -> str:
    """Remove characters that are not allowed in the filename
    and convert spaces to underscores."""
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"[\s-]+", "_", title).strip("_")
    return title


# source: // https://www.cda.pl/js/player.js?t=1676342296
def decrypt_url(url: str) -> str:
    for p in ("_XDDD", "_CDA", "_ADC", "_CXD", "_QWE", "_Q5", "_IKSDE"):
        url = url.replace(p, "")
    url = urllib.parse.unquote(url)
    b = []
    for c in url:
        f = c if isinstance(c, int) else ord(c)
        b.append(chr(33 + (f + 14) % 94) if 33 <= f <= 126 else chr(f))
    a = "".join(b)
    a = a.replace(".cda.mp4", "")
    a = a.replace(".2cda.pl", ".cda.pl")
    a = a.replace(".3cda.pl", ".cda.pl")
    if "/upstream" in a:
        a = a.replace("/upstream", ".mp4/upstream")
        return "https://" + a
    return "https://" + a + ".mp4"


def get_random_agent() -> str:
    """Get random user agent."""
    USER_AGENTS = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0"
            " Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0"
            " Safari/537.36"
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
            " Gecko) Chrome/108.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1"
            " Safari/605.1.15"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15"
            " (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
        ),
    ]
    return random.choice(USER_AGENTS)


@retry(
    retry=retry_if_exception_type(HTTPError),
    wait=wait_fixed(1),
    stop=(stop_after_attempt(3) | stop_after_delay(5)),
    reraise=True,
)
async def get_request(
    url: str, session: aiohttp.ClientSession, headers: dict[str, str]
) -> aiohttp.ClientResponse:
    """Get request with random user agent."""
    headers["User-Agent"] = get_random_agent()
    try:
        response = await session.get(url, headers=headers)
        response.raise_for_status()
    except aiohttp.ClientResponseError as e:
        raise HTTPError(
            f"HTTP error [{e.status}]: {e.message}. Pomijam ...", e.status
        )
    else:
        return response


def clear() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")
