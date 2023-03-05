import asyncio
from pathlib import Path


class DownloadOptions:
    semaphore: asyncio.Semaphore

    def __init__(
        self,
        directory: Path = Path("."),
        resolution: str = "najlepsza",
        overwrite: bool = False,
        nthreads: int = 3,
        quiet: bool = False,
    ) -> None:
        self.directory = directory
        self.resolution = resolution
        self.overwrite = overwrite
        self.nthreads = nthreads
        self.quiet = quiet
