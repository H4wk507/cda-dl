import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.downloader import Downloader


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
        "-o",
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="Nadpisz pliki, jeśli istnieją",
    )
    parser.add_argument(
        "urls",
        metavar="URL",
        type=str,
        nargs="+",
        help="URL(y) do filmu(ów)/folder(ów) do pobrania",
    )
    return parser.parse_args(args)


def main() -> None:
    my_args = parse_args(sys.argv[1:])
    Downloader(my_args)


if __name__ == "__main__":
    main()


# TODO: reformat tests
# TODO: partial files for easier resuming the download
# TODO: maybe support for premium videos on login?
