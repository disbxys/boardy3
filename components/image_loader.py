import logging
from typing import List

from PyQt6.QtCore import pyqtSignal, QThread

from database_manager import DatabaseManager, DatabaseItemExists
from models import Image


class ImageLoader(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager, file_paths: List[str]):
        super().__init__()
        self.db_manager = db_manager
        self.file_paths = file_paths

    
    def run(self):
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            try:
                self.db_manager.add_image(file_path, tags=["general"])
            except DatabaseItemExists:
                # Skip items that already exist in the database
                pass

            # Update progress
            self.progress_updated.emit(int((i + 1) / total_files * 100))

        self.finished.emit()