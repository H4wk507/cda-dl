import argparse
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


def is_video(url: str) -> bool:
    video_regex = r"cda\.pl\/video\/.+$"
    return re.search(video_regex, url) is not None


def is_folder(url: str) -> bool:
    folder_regex = r"cda\.pl\/.+\/folder\/.+$"
    return re.search(folder_regex, url) is not None


def download_video(url: str, driver: webdriver.Firefox) -> None:
    driver.get(url)
    video_soup = BeautifulSoup(driver.page_source, "html.parser")
    download_url = video_soup.find_all("video")[0]
    title = video_soup.find_all("h1")[0].text
    title = title.replace(" ", "_")
    video_stream = requests.get(download_url["src"], stream=True)
    print(f"Downloading {title}.mp4")
    with open(f"{title}.mp4", "wb") as f:
        for chunk in video_stream.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    print(f"Finished downloading {title}.mp4")


# TODO: automatically select the best quality
# TODO: add flag to specify destination folder
# TODO: add progress bar for downloading video
# TODO: when downloading folder traverse next pages
# TODO: resume folder download if it was previously cancelled
# TODO: windows support
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    CDA_URL = "https://www.cda.pl"
    # url = "https://www.cda.pl/Pokemon_Odcinki_PL/folder/1980929"
    # url = "https://www.cda.pl/video/9122600a"
    url = input("Enter url for download: ")
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()), options=options
    )
    if is_video(url):
        download_video(url, driver)
    elif is_folder(url):
        driver.get(url)
        folder_soup = BeautifulSoup(driver.page_source, "html.parser")
        videos = folder_soup.find_all("a", href=True, class_="thumbnail-link")
        for video in videos:
            video_url = CDA_URL + video["href"]
            download_video(video_url, driver)
    else:
        print("Could not recognize the url. Aborting...")
        exit(1)
