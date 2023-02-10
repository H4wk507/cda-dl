import re


def is_video(url: str) -> bool:
    """Check if url is a cda video."""
    video_regex = re.compile(
        r"""https?://(?:(?:www|ebd)\.)?cda\.pl/
        (?:video|[0-9]+x[0-9]+)/([0-9a-z]+)""",
        re.VERBOSE | re.IGNORECASE,
    )
    match = video_regex.match(url)
    return match is not None


def is_folder(url: str) -> bool:
    """Check if url is a cda folder."""
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
    match = folder_regex1.match(url) or folder_regex2.match(url)
    return match is not None


def get_adjusted_title(title: str) -> str:
    """Remove characters that are not allowed in the filename
    and convert spaces to underscores."""
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"[\s-]+", "_", title).strip("_")
    return title
