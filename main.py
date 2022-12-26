import argparse
import re
import platform
from os import path
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def is_video(url: str) -> bool:
    video_regex = r"cda\.pl\/video\/.+$"
    return re.search(video_regex, url) is not None


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


def get_filepath(destination: str, title: str, user_os: str) -> str:
    if user_os == "Windows":
        filepath = fr"{destination}\{title}.mp4"
    else:
        filepath = fr"{destination}/{title}.mp4"
    return filepath


def download_video(
    url: str, driver: webdriver.Chrome, destination: str, user_os: str
) -> None:
    driver.get(url)
    video_soup = BeautifulSoup(driver.page_source, "html.parser")
    download_url = video_soup.find_all("video")[0]
    title = video_soup.find_all("h1")[0].text
    title = adjust_title(title, user_os)
    video_stream = requests.get(download_url["src"], stream=True)
    filepath = get_filepath(destination, title, user_os)
    print(f"Downloading {title}.mp4 to {filepath}")
    with open(f"{filepath}", "wb") as f:
        for chunk in video_stream.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    print(f"Finished downloading {title}.mp4")


# TODO: automatically select the best quality
# TODO: add flag to specify destination folder
# TODO: add progress bar for downloading video
# TODO: when downloading folder traverse next pages
# TODO: resume folder download if it was previously cancelled
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    USER_OS = platform.system()
    CDA_URL = "https://www.cda.pl"
    # url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
    # url = "https://www.cda.pl/video/9122600a"
    url = input("Enter url for download: ")
    destination = input("Enter path to the directory: ")
    destination = path.abspath(path.expanduser(path.expandvars(destination)))
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()), options=options
    )
    if is_video(url):
        download_video(url, driver, destination, USER_OS)
    elif is_folder(url):
        driver.get(url)
        folder_soup = BeautifulSoup(driver.page_source, "html.parser")
        videos = folder_soup.find_all("a", href=True, class_="thumbnail-link")
        for video in videos:
            video_url = CDA_URL + video["href"]
            download_video(video_url, driver, destination, USER_OS)
    else:
        print("Could not recognize the url. Aborting...")
        exit(1)
