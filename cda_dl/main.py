import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cda_dl.downloader import Downloader
from cda_dl.version import __version__


class CustomHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog: str):
        super().__init__(prog, max_help_position=40, width=80)

    def _format_action_invocation(self, action: argparse.Action) -> str:
        if not action.option_strings or action.nargs == 0:
            return super()._format_action_invocation(action)
        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return ", ".join(action.option_strings) + " " + args_string


def parse_args(args: list[str]) -> argparse.Namespace:
    def fmt(prog: str) -> CustomHelpFormatter:
        return CustomHelpFormatter(prog)

    parser = argparse.ArgumentParser(
        prog="cda-dl",
        usage="%(prog)s [OPCJE] URL [URL...]",
        description="Downloader do filmów i folderów z cda.pl",
        formatter_class=fmt,
    )
    # parser = argparse.ArgumentParser(
    #    prog="cda-dl",
    #    description="Downloader do filmów i folderów z cda.pl",
    #    add_help=False,
    #    formatter_class=fmt,
    # )
    # parser.add_argument("-h", "--help",action="help",help=argparse.SUPPRESS)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Wyświetl wersję programu",
    )
    parser.add_argument(
        "-d",
        "--directory",
        metavar="PATH",
        dest="directory",
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
        metavar="RES",
        dest="resolution",
        type=str,
        default="najlepsza",
        help="Pobierz film w podanej rozdzielczości (domyślnie '%(default)s')",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Nadpisz pliki, jeśli istnieją",
    )
    parser.add_argument(
        "-t",
        "--threads",
        metavar="N",
        dest="nthreads",
        type=int,
        default=3,
        help="Ustaw liczbę wątków (domyślnie %(default)s)",
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


# TODO: write CI on github
# TODO: better ui: https://github.com/Textualize/rich
# TODO: install via pip install cda-dl
# TODO: maybe support for premium videos on login?
