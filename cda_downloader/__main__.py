import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_downloader.main import Downloader


def parse_args(args: list[str]) -> argparse.Namespace:
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
        dest="list_resolutions",
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
        "urls",
        metavar="URL",
        type=str,
        nargs="+",
        help="URL(s) to video(s)/folder(s) to download",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    Downloader(args)
