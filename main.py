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


def get_args() -> argparse.Namespace:
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
        "url", metavar="URL", type=str, help="URL to video/folder to download"
    )
    return parser.parse_args()


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


def get_best_quality(url: str) -> str:
    """Get best quality available from video at url."""
    response = requests.get(url)
    video_soup = BeautifulSoup(response.text, "html.parser")
    video_id = get_videoid(url)
    video_info = json.loads(
        video_soup.find("div", {"id": f"mediaplayer{video_id}"}).attrs[
            "player_data"
        ]
    )
    qualities = video_info["video"]["qualities"]
    return list(qualities)[-1]


def download_video(
    url: str, driver: webdriver.Chrome, directory: str, user_os: str
) -> None:
    best_quality = get_best_quality(url)
    video_id = get_videoid(url)
    driver.get(
        f"https://ebd.cda.pl/1920x1080/{video_id}/?wersja={best_quality}"
    )
    video_soup = BeautifulSoup(driver.page_source, "html.parser")
    video = video_soup.find("video")
    title = video_soup.find("h1").text.strip("\n")
    title = adjust_title(title, user_os)
    video_stream = requests.get(video["src"], stream=True)
    Path(directory).mkdir(parents=True, exist_ok=True)
    filepath = get_filepath(directory, title, user_os)
    print(f"Downloading {filepath} [{best_quality}]")
    with open(filepath, "wb") as f:
        for chunk in video_stream.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    print(f"Finished downloading {title}.mp4")


def download_folder(
    url: str,
    driver: webdriver.Chrome,
    directory: str,
    user_os: str,
    cda_url: str,
) -> None:
    driver.get(url)
    folder_soup = BeautifulSoup(driver.page_source, "html.parser")
    videos = folder_soup.find_all("a", href=True, class_="thumbnail-link")
    for video in videos:
        video_url = cda_url + video["href"]
        download_video(video_url, driver, directory, user_os)


# TODO: add flag to specify the quality
# TODO: add progress bar for downloading video
# TODO: when downloading folder traverse next pages
# TODO: resume folder download if it was previously cancelled
# TODO: multiple urls
# url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
# url = "https://www.cda.pl/video/9122600a"
if __name__ == "__main__":
    args = get_args()
    USER_OS = platform.system()
    CDA_URL = "https://www.cda.pl"
    url = args.url
    directory = args.directory
    directory = path.abspath(path.expanduser(path.expandvars(directory)))
    chrome_options = get_options()
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options,
    )
    if is_video(url):
        download_video(url, driver, directory, USER_OS)
    elif is_folder(url):
        download_folder(url, driver, directory, USER_OS, CDA_URL)
    else:
        print("Could not recognize the url. Aborting...")
        exit(1)
    driver.close()
