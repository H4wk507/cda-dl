import argparse
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_downloader.downloader import Downloader


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    parser.add_argument(
        "-d",
        "--directory",
        metavar="\b",
        type=str,
        default=".",
        help="Ustaw docelowy katalog (domyślnie '%(default)s')",
    )
    parser.add_argument(
        "-R",
        "--resolutions",
        dest="list_resolutions",
        action="store_true",
        help="Wyświetl dostępne rozdzielczości (dla filmu)",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        metavar="\b",
        type=str,
        default="najlepsza",
        help="Pobierz film w podanej rozdzielczości (domyślnie '%(default)s')",
    )
    parser.add_argument(
        "urls",
        metavar="URL",
        type=str,
        nargs="+",
        help="URL(y) do filmu(ów)/folder(ów) do pobrania",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    Downloader(args)


# TODO: add setup.py file for installing
# TODO: write README.md in polish
# TODO: resume folder download if it was previously cancelled
# TODO: maybe support for premium videos on login?
# TODO: better error handling
