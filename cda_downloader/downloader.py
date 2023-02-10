import argparse
import os
from cda_downloader.utils import is_video, is_folder
from cda_downloader.video import Video
from cda_downloader.folder import Folder


class Downloader:
    urls: list[str]
    directory: str
    resolution: str

    def __init__(self, args: argparse.Namespace) -> None:
        self.urls = [url.strip() for url in args.urls]
        self.directory = os.path.abspath(
            os.path.expanduser(os.path.expandvars(args.directory))
        )
        self.resolution = args.resolution
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        if args.list_resolutions:
            self.list_resolutions_and_exit()
        self.handle_r_flag()
        self.main()

    def list_resolutions_and_exit(self) -> None:
        """List available resolutions for a video and exit."""
        for url in self.urls:
            if is_video(url):
                print(f"Dostępne rozdzielczości dla {url}:")
                v = Video(url, self.directory, self.resolution, self.headers)
                v.video_id = v.get_videoid()
                resolutions = v.get_resolutions()
                for res in resolutions:
                    print(res)
            elif is_folder(url):
                exit(
                    f"Flaga -R jest dostępna tylko dla filmów. {url} jest"
                    " folderem!"
                )
            else:
                exit(f"Nie rozpoznano adresu url: {url}")
        exit()

    def handle_r_flag(self) -> None:
        for url in self.urls:
            if self.resolution != "najlepsza":
                if is_video(url):
                    v = Video(
                        url, self.directory, self.resolution, self.headers
                    )
                    v.video_id = v.get_videoid()
                    v.resolutions = v.get_resolutions()
                    v.check_resolution()
                elif is_folder(url):
                    exit(
                        f"Flaga -r jest dostępna tylko dla filmów. {url} jest"
                        " folderem!"
                    )
                else:
                    exit(f"Nie rozpoznano adresu url: {url}")

    def main(self) -> None:
        for url in self.urls:
            if is_video(url):
                Video(
                    url, self.directory, self.resolution, self.headers
                ).download_video()
            elif is_folder(url):
                Folder(url, self.directory, self.headers).download_folder()
            else:
                exit(f"Nie rozpoznano adresu url: {url}")
        print("Skończono robotę.")
