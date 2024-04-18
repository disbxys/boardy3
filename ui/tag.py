import os
from typing import Sequence

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QCloseEvent, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget
)
from sqlalchemy import Column

from database.models import Tag
from ui.layout import FlowLayout


class TagWidget(QWidget):
    def __init__(self, tag: Tag):
        super().__init__()

        self.tag_id = str(tag.id)
        self.tag_name = str(tag.name)

        self.checkbox = QCheckBox()
        self.tag_description = QLabel(self.tag_name)

        layout = QHBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.tag_description)

        self.setLayout(layout)


class TagsWindow(QWidget):
    """A class for displaying an image's tag(s)"""

    def __init__(self, tags: list[Tag] | None = None):
        super().__init__()

        # Define an area to display tags
        self.scroll_area = QScrollArea()
        self.tags_list_widget = FlowLayout(self.scroll_area)
        
        if tags is not None:
            # self.tags_list.extend(TagWidget(tag) for tag in tags)
            for tag in tags:
                self.tags_list_widget.addWidget(TagWidget(tag))

        # Set scroll area properties
        self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)