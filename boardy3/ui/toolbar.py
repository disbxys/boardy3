import math

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QToolBar,
    QWidget
)

from boardy3.database.database_manager import DatabaseManager


class ToolBar(QWidget):
    page_updated = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__()

        self.db_manager = db_manager

        self.toolbar = QToolBar()

        self.current_page = 1

        # Previous Page Action
        prev_page_action = QAction("<", self)
        prev_page_action.triggered.connect(self.load_previous_page)
        self.toolbar.addAction(prev_page_action)

        # Current Page Label
        # TODO: Make editable for faster searching.
        self.page_label = QLabel()
        self.toolbar.addWidget(self.page_label)

        # Next Page Action
        next_page_action = QAction(">", self)
        next_page_action.triggered.connect(self.load_next_page)
        self.toolbar.addAction(next_page_action)

        # Page Size Combo Box
        self.page_size_combo_box = QComboBox()
        self.page_size_combo_box.setMaximumWidth(50)
        self.page_size_combo_box.addItems(["10", "20", "30", "40", "50"])
        self.page_size_combo_box.currentTextChanged.connect(self.reset_page)

        # Update the page label after all components are created.
        # Doesn't matter (I think) if placed before or after
        # adding to layout.
        self.update_page_label()

        layout = QHBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.page_size_combo_box)

        self.setLayout(layout)


    def update_page_label(self) -> None:
        self.page_label.setText(f"Page {self.current_page} of {self._get_max_page_count()}")

    
    def load_previous_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1

            self.page_updated.emit()

            self.update_page_label()


    def load_next_page(self) -> None:
        # Check if there are more pages
        more_pages = len(self.db_manager.search_images(
            list(),
            self.current_page+1,
            int(self.page_size_combo_box.currentText())
        )) > 0

        if more_pages:
            self.current_page += 1

            self.page_updated.emit()

            self.update_page_label()


    def reset_page(self) -> None:
        self.current_page = 1

        self.page_updated.emit()

        self.update_page_label()

    
    def _get_max_page_count(self) -> int:
        """
        Calculate the last page based on the per_page value and round up
        or set to one if there are no images.
        """
        return max(
            math.ceil(self.db_manager.get_images_count() / self.get_current_page_size()),
            1
        )
    

    def get_current_page_size(self) -> int:
        return int(self.page_size_combo_box.currentText())