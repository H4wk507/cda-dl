import re
import os


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


def clear() -> None:
    """Clears the terminal screen"""
    os.system("cls" if os.name == "nt" else "clear")
