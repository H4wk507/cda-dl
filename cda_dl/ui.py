from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table


class RichUI:
    progbar_video: Progress | None
    progbar_folder: Progress | None
    task_id: TaskID

    def __init__(self, table: Table) -> None:
        self.table = table
        self.progbar_video = None
        self.progbar_folder = None

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

    def add_task_folder(self, filename: str, total: int) -> None:
        assert self.progbar_folder
        self.task_id = self.progbar_folder.add_task(
            "download folder",
            filename=filename,
            total=total,
        )

    def update_task_folder(self, advance: int) -> None:
        assert self.progbar_folder
        self.progbar_folder.update(self.task_id, advance=advance)

    def remove_task_folder(self) -> None:
        assert self.progbar_folder
        self.progbar_folder.remove_task(self.task_id)
