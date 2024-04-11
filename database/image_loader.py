import os

import magic
from PyQt6.QtCore import pyqtSignal, QThread

from database.database_manager import DatabaseManager, DatabaseItemExists


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
            except DatabaseItemExists:
                # Skip items that already exist in the database
                pass
            except UnicodeDecodeError:
                # Skip bad files
                # This should come from the python magic lib
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
    finished = pyqtSignal()

    def __init__(
            self,
            db_manager: DatabaseManager,
            dir_path: str
    ) -> None:
        super().__init__()
        self.db_manager = db_manager
        self.dir_path = dir_path

    
    def run(self) -> None:
        image_file_count = 0
        for (dirpath, _, filenames) in os.walk(self.dir_path):
            for filename in filenames:
                fullpath = os.path.join(dirpath, filename)
                try:
                    if is_image(fullpath):
                        # print(fullpath)
                        self.db_manager.add_image(fullpath, tags=["general"])
                except DatabaseItemExists:
                    # Skip items that already exist in the database
                    pass
                except UnicodeDecodeError:
                    # Skip bad files
                    # This should come from the python magic lib
                    pass

                image_file_count += 1
                self.progress_updated.emit(image_file_count)

        self.finished.emit()


def is_image(file_path: str) -> bool:
    print(file_path)
    mtype = magic.from_file(file_path, mime=True)
    return mtype.startswith("image/")