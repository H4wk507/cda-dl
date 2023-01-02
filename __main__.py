from main import Downloader
import argparse


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
        "url", metavar="URL", type=str, help="URL to video/folder to download"
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    Downloader(args)
