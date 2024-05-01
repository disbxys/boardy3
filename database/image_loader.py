from collections.abc import Iterator
import os

import magic
from PyQt6.QtCore import pyqtSignal, QThread

from database.database_manager import DatabaseManager, DatabaseItemExists
from utils import get_logger


logger = get_logger(__name__)


class ImageLoader(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(
            self,
            db_manager: DatabaseManager,
            file_paths: list[str]
    ) -> None:
        super().__init__()
        self.db_manager = db_manager
        self.file_paths = file_paths

    
    def run(self) -> None:
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            try:
                if is_image(file_path):
                    self.db_manager.add_image(file_path, tags=["general"])
                    logger.info(f"New image added {file_path}.")
            except DatabaseItemExists:
                # Skip items that already exist in the database
                logger.debug(f"Image <{file_path}> already exists.")
                pass

            # Update progress
            self.progress_updated.emit(int((i + 1) / total_files * 100))

        self.finished.emit()


class DirImageLoader(QThread):
    """
    Similar to ImageLoader, except a dirpath is given and
    is recursively iterated through. Each image is processed
    similar to ImageLoader
    """
    progress_updated = pyqtSignal(int)
    scan_completed = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(
            self,
            db_manager: DatabaseManager,
            dirpath: str
    ) -> None:
        super().__init__()
        self.db_manager = db_manager
        self.dirpath = dirpath
        self.total_files = 0

    
    def run(self) -> None:
        self.total_files = len(list(self._find_images()))
        self.scan_completed.emit(self.total_files)

        for i, file_path in enumerate(self._find_images()):
            try:
                if is_image(file_path):
                    self.db_manager.add_image(file_path, tags=["general"])
                    logger.info(f"New image added {file_path}.")
            except DatabaseItemExists:
                # Skip items that already exist in the database
                logger.debug(f"Image <{file_path}> already exists.")
                pass

            # Update progress
            self.progress_updated.emit(int((i + 1) / self.total_files * 100))

        self.finished.emit()

    
    def _find_images(self) -> Iterator[str]:
        """
        Iterate through all files and subdirectories of
        dirpath and return a generator of all image files.
        """
        for (dirpath, _, filenames) in os.walk(self.dirpath):
            for filename in filenames:
                yield os.path.join(dirpath, filename)


def is_image(file_path: str) -> bool:
    try:
        mtype = magic.from_file(file_path, mime=True)
        return mtype.startswith("image/")
    except UnicodeDecodeError:
        # This should come from the python magic lib
        return False
