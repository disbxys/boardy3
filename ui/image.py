import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QLabel,
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
            db_id: int | Column[int],
            image_path: str,
            width: int | None = None,
            height: int | None = None,
            db_manager: DatabaseManager | None = None
    ):
        super().__init__()

        self.image_path = image_path
        self.db_id = db_id

        self.db_manager = db_manager or DatabaseManager()

        _pixmap = QPixmap(self.image_path)
        _w = width if width else _pixmap.width()
        _h = height if height else _pixmap.height()
        self.setPixmap(_pixmap.scaled(
            _w, _h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

        self.mousePressEvent = self.open_image_window

    
    @pyqtSlot()
    def open_image_window(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.image_window = ImageWindow(self.db_id, self.image_path)
            self.image_window.show()

    
    def fetch_tags(self) -> list[Tag]:
        return self.db_manager.get_tags_by_image_id(self.db_id)


class ImageWindow(QMainWindow):
    def __init__(self, db_id: int | Column[int], image_path: str):
        super().__init__()

        # Use the image filename as the window title
        self.setWindowTitle(os.path.splitext(os.path.basename(image_path))[0])

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Display image
        self.image_widget = ImageWidget(db_id, image_path, 800, 800)

        # Display image tags
        tags_list = self.fetch_tags()     # Get image tags from database
        self.tags_panel = TagsWindow(tags_list)

        layout = QVBoxLayout()
        layout.addWidget(self.image_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.tags_panel)

        self.central_widget.setLayout(layout)

        # Redefine image mouse press event to do nothing. Otherwise,
        # it would create a new image window every left click.
        self.image_widget.mousePressEvent = self.mousePressEvent


    def fetch_tags(self) -> list[Tag]:
        return self.image_widget.fetch_tags()

    
    def mousePressEvent(self, ev: QMouseEvent):
        return super().mousePressEvent(ev)
