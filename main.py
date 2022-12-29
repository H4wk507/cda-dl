import argparse
import re
import platform
import json
from os import path
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--directory",
        metavar="\b",
        type=str,
        default=".",
        help="Set destination directory (default '%(default)s')",
    )
    parser.add_argument(
        "-R",
        "--resolutions",
        action="store_true",
        help="List available resolutions (for a video)",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        metavar="\b",
        type=str,
        default="best",
        help=(
            "Download video using specified resolution (default '%(default)s')"
        ),
    )
    parser.add_argument(
        "url", metavar="URL", type=str, help="URL to video/folder to download"
    )
    args = parser.parse_args()
    return args


def get_options() -> Options:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")
    return chrome_options


def is_video(url: str) -> bool:
    video_regex = r"cda\.pl\/video\/.+$"
    return re.search(video_regex, url) is not None


def get_videoid(url: str) -> str:
    video_regex = r"cda\.pl\/video\/(.+)$"
    match = re.search(video_regex, url)
    return match.group(1) if match else ""


def is_folder(url: str) -> bool:
    folder_regex = r"cda\.pl\/.+\/folder\/.+$"
    return re.search(folder_regex, url) is not None


def adjust_title(title: str, user_os: str) -> str:
    title = title.replace(" ", "_")
    if user_os == "Windows":
        title = re.sub(r'[<>:"\/\\|?*.]', "", title)
    elif user_os == "Darwin":
        title = re.sub(r"[:\/]", "", title)
    else:
        title = re.sub(r"[\/]", "", title)
    return title


def get_filepath(directory: str, title: str, user_os: str) -> str:
    if user_os == "Windows":
        filepath = rf"{directory}\{title}.mp4"
    else:
        filepath = rf"{directory}/{title}.mp4"
    return filepath


def get_resolutions(url: str) -> list[str]:
    """Get available video resolutions at the url."""
    response = requests.get(url)
    video_soup = BeautifulSoup(response.text, "html.parser")
    video_id = get_videoid(url)
    video_info = json.loads(
        video_soup.find("div", {"id": f"mediaplayer{video_id}"}).attrs[
            "player_data"
        ]
    )
    resolutions = video_info["video"]["qualities"]
    return list(resolutions)


def is_valid_resolution(url: str, resolution: str) -> bool:
    return resolution in get_resolutions(url)


def get_best_resolution(url: str) -> str:
    """Get best video resolution available at the url."""
    return get_resolutions(url)[-1]


def download_video(
    url: str,
    driver: webdriver.Chrome,
    directory: str,
    resolution: str,
    user_os: str,
) -> None:
    if resolution == "best":
        resolution = get_best_resolution(url)
    if not is_valid_resolution(url, resolution):
        print(f"{resolution} resolution is not available for {url}")
        return
    video_id = get_videoid(url)
    driver.get(f"https://ebd.cda.pl/1920x1080/{video_id}/?wersja={resolution}")
    video_soup = BeautifulSoup(driver.page_source, "html.parser")
    video = video_soup.find("video")
    title = video_soup.find("h1").text.strip("\n")
    title = adjust_title(title, user_os)
    video_stream = requests.get(video["src"], stream=True)
    Path(directory).mkdir(parents=True, exist_ok=True)
    filepath = get_filepath(directory, title, user_os)
    print(f"Downloading {filepath} [{resolution}]")
    with open(filepath, "wb") as f:
        for chunk in video_stream.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    print(f"Finished downloading {title}.mp4")


def download_folder(
    url: str,
    driver: webdriver.Chrome,
    directory: str,
    resolution: str,
    user_os: str,
    cda_url: str,
) -> None:
    if resolution != "best":
        print("-r flag is only available for videos.")
        return
    driver.get(url)
    folder_soup = BeautifulSoup(driver.page_source, "html.parser")
    videos = folder_soup.find_all("a", href=True, class_="thumbnail-link")
    for video in videos:
        video_url = cda_url + video["href"]
        download_video(video_url, driver, directory, resolution, user_os)


def list_resolutions(url: str) -> None:
    if not is_video(url):
        print("-R flag is only available for videos.")
    else:
        print(f"Available resolutions for {url}:")
        resolutions = get_resolutions(url)
        for r in resolutions:
            print(r)


# TODO: add progress bar for downloading video
# TODO: when downloading folder traverse next pages
# TODO: resume folder download if it was previously cancelled
# TODO: multiple urls
# url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
# url = "https://www.cda.pl/video/9122600a"
if __name__ == "__main__":
    args = parse_args()
    USER_OS = platform.system()
    CDA_URL = "https://www.cda.pl"
    if args.resolutions:
        list_resolutions(args.url)
        exit(1)
    directory = path.abspath(path.expanduser(path.expandvars(args.directory)))
    chrome_options = get_options()
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options,
    )
    if is_video(args.url):
        download_video(args.url, driver, directory, args.resolution, USER_OS)
    elif is_folder(args.url):
        download_folder(
            args.url, driver, directory, args.resolution, USER_OS, CDA_URL
        )
    else:
        print("Could not recognize the url. Aborting...")
