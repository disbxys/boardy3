from collections.abc import Iterable
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget
)

from boardy3.ui.layout import clear_layout


class WidgetList(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.list_layout = QVBoxLayout()
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setLayout(self.list_layout)


    def add(self, item: QWidget) -> None:
        self.list_layout.addWidget(item)

    
    def extend(self, items: Iterable[QWidget]) -> None:
        for item in items:
            self.add(item)


    def clear(self) -> None:
        clear_layout(self.list_layout)


    def set_header_row(self) -> None:
        """
        Add a list item to the list to act as a header row.
        Should be called after clearing the layout.
        """
        raise NotImplementedError()