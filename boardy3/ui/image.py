import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QHBoxLayout,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget
)

from boardy3.database.database_manager import DatabaseItemDoesNotExist, DatabaseManager
from boardy3.database.models import Tag
from boardy3.ui.tag import TagsWindow


class ImageWidget(QLabel):
    def __init__(
            self,
            db_id: int,
            width: int | None = None,
            height: int | None = None,
            db_manager: DatabaseManager | None = None,
            detached: bool = False
    ):
        super().__init__()

        # Image id from database
        self.db_id = db_id

        self.db_manager = db_manager or DatabaseManager()
        self.detached = detached

        # Grab image from database
        self.image_ = self.db_manager.get_image(self.db_id)
        if self.image_ is None:
            raise ValueError(f"Invalid image id: {self.db_id}.")
        self.image_path = self.db_manager.get_image_path(self.image_.filename)

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

        # Shift instantiation position of image window top left
        self.setGeometry(100, 100, self.width(), self.height())

        # Use the image filename as the window title
        self.setWindowTitle(os.path.splitext(os.path.basename(image_path))[0])

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Display image
        self.image_widget = ImageWidget(db_id, 800, 800, detached=True)

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

        # Keep window size fixed after creating everything in the window.
        match self.layout_:
            case QVBoxLayout():
                self.setFixedSize(
                    self.image_widget.pixmap().width()+1,
                    self.image_widget.pixmap().height() + self.tags_panel.height() + 50
                )
            case QHBoxLayout():
                self.setFixedSize(
                    self.image_widget.pixmap().width() + self.tags_panel.width() + 50,
                    self.image_widget.pixmap().height()+1
                )

        self.central_widget.setLayout(self.layout_)


    def fetch_tags(self) -> list[Tag]:
        return self.image_widget.fetch_tags()

    
    def mousePressEvent(self, ev: QMouseEvent):
        return super().mousePressEvent(ev)


class ImageUrlInputDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Enter Urls")
        # self.setGeometry(200, 200, 300, 150)

        self.input_box = QPlainTextEdit()

        self.warning_label = QLabel("Enter one url per line")
        
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit_access_token)

        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.input_box)
        layout.addWidget(self.warning_label)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)
    
    def submit_access_token(self):
        urls_input = self.input_box.toPlainText().strip()
        urls_input = re.sub(r"\s{1,}", " ", urls_input)

        self.image_urls = urls_input.split()
        
        self.close()
