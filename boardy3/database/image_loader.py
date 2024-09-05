from collections.abc import Iterator
import os
import tempfile
from urllib.parse import urlparse

import magic
from PyQt6.QtCore import pyqtSignal, QThread
import requests
from requests_ratelimiter import LimiterSession

from boardy3.database.database_manager import DatabaseManager, DatabaseItemExists
from boardy3.utils import get_logger


requests.packages.urllib3.disable_warnings()  # type: ignore

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
                    self.db_manager.add_image(file_path)
                    logger.info(f"New image added {file_path}.")
                elif is_video(file_path):
                    self.db_manager.add_image(file_path, is_video=True)
                    logger.info(f"New video added {file_path}.")
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
    similar to ImageLoader.
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


class NetworkImageLoader(QThread):
    """
    Similar to ImageLoard, except a url is given to download an
    image from. Each image is processed similar to ImageLoader.
    """
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(
            self,
            db_manager: DatabaseManager,
            image_urls: list[str]
    ) -> None:
        super().__init__()
        self.db_manager = db_manager
        self.image_urls = image_urls
        self.session = self._create_session()

    
    def run(self) -> None:
        for i, image_url in enumerate(self.image_urls):

            # Create a tmp file to temporarily store images
            with open(tempfile.NamedTemporaryFile(dir=self.db_manager.image_dir_path).name, "wb+") as tmp_file:

                try:
                    if not self._validate_url(image_url):
                        logger.debug(f"Invalid url skipped: <{image_url}>")
                        continue

                    with self.session.get(image_url) as response:
                        if not response.ok: continue

                        # Write content to tmp file
                        tmp_file.write(response.content)

                        if is_image(tmp_file.name):
                            self.db_manager.add_image(tmp_file.name, tags=["general"])
                            logger.info(f"New image added {image_url}.")

                except DatabaseItemExists:
                    # Skip items that already exist in the database
                    logger.debug(f"Image <{image_url}> already exists.")
                    pass
                finally:
                    if not tmp_file.closed:
                        tmp_file.close()
                        os.remove(tmp_file.name)
            
            self.progress_updated.emit(int((i + 1) / len(self.image_urls) * 100))

        self.finished.emit()

        
    @staticmethod
    def _create_session() -> requests.Session:
        session = LimiterSession(per_minute=50)
        session.verify = False
        return session
    

    def _validate_url(self, url: str) -> bool:
        parsed = urlparse(url)

        if parsed.scheme not in ["http", "https"]:
            return False
        
        if parsed.netloc.strip() == "":
            return False
        
        return True
        


def is_image(file_path: str) -> bool:
    try:
        mtype = magic.from_file(file_path, mime=True)
        return mtype.startswith("image/")
    except UnicodeDecodeError:
        # This should come from the python magic lib
        return False


def is_video(file_path: str) -> bool:
    try:
        mtype = magic.from_file(file_path, mime=True)
        return mtype.startswith("video/")
    except UnicodeDecodeError:
        # This should come from the python magic lib
        return False
