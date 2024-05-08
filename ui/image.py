import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget
)
from sqlalchemy import Column

from database.database_manager import DatabaseManager
from database.models import Tag
from ui.tag import TagsWindow


class ImageWidget(QLabel):
    def __init__(
            self,
            db_id: int,
            image_path: str,
            width: int | None = None,
            height: int | None = None,
            db_manager: DatabaseManager | None = None,
            detached: bool = False
    ):
        super().__init__()

        self.image_path = image_path
        self.db_id = db_id

        self.db_manager = db_manager or DatabaseManager()
        self.detached = detached

        _pixmap = QPixmap(self.image_path)
        _w = width if width else _pixmap.width()
        _h = height if height else _pixmap.height()
        self.setPixmap(_pixmap.scaled(
            _w, _h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))


    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if not self.detached:
            # Do not create a detached image window if this
            # widget is already detached.
            if ev.button() == Qt.MouseButton.LeftButton:
                """Creates a detached window containing an image. """
                self.image_window = ImageWindow(self.db_id, self.image_path)
                self.image_window.show()

    
    def fetch_tags(self) -> list[Tag]:
        return self.db_manager.get_tags_by_image_id(self.db_id)


class ImageWindow(QMainWindow):
    def __init__(self, db_id: int, image_path: str):
        super().__init__()

        # Use the image filename as the window title
        self.setWindowTitle(os.path.splitext(os.path.basename(image_path))[0])

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Display image
        self.image_widget = ImageWidget(db_id, image_path, 800, 800, detached=True)

        if self.image_widget.pixmap().width() > self.image_widget.pixmap().height():
            portrait = False
            self.layout_ = QVBoxLayout()
        else:
            portrait = True
            self.layout_ = QHBoxLayout()

        # Create a panel to contain tags
        self.tags_panel = TagsWindow(self.image_widget.db_id, portrait=portrait)

        # self.layout_ = QVBoxLayout()
        self.layout_.addWidget(self.image_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout_.addWidget(self.tags_panel, stretch=1)

        self.central_widget.setLayout(self.layout_)


    def fetch_tags(self) -> list[Tag]:
        return self.image_widget.fetch_tags()

    
    def mousePressEvent(self, ev: QMouseEvent):
        return super().mousePressEvent(ev)
