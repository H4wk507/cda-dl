from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    SpinnerColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.panel import Panel

from typing import Optional


class RichUI:
    def __init__(
        self,
        table: Table,
        progbar_video: Optional[Progress] = None,
        progbar_folder: Optional[Progress] = None,
    ) -> None:
        self.table = table
        self.progbar_video = progbar_video
        self.progbar_folder = progbar_folder

    def set_progress_bar_video(self, color: str) -> None:
        self.progbar_video = Progress(
            SpinnerColumn(),
            TextColumn(
                f"[{color}]{{task.fields[filename]}}",
                justify="right",
            ),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            transient=True,
        )

    def set_progress_bar_folder(self, color: str) -> None:
        self.progbar_folder = Progress(
            TextColumn(
                f"[{color}]{{task.fields[filename]}}",
                justify="right",
            ),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "{task.completed} z {task.total} Pobranych Filmów lub/i Folderów",
            transient=True,
        )

    def add_row_video(self, border: str) -> None:
        assert self.table and self.progbar_video
        self.table.add_row(
            Panel.fit(
                self.progbar_video,
                title="Filmy",
                border_style=border,
                padding=(1, 1),
            )
        )

    def add_row_folder(self, border: str) -> None:
        assert self.table and self.progbar_folder
        self.table.add_row(
            Panel.fit(
                self.progbar_folder,
                title="Foldery",
                border_style=border,
                padding=(1, 1),
            )
        )
