from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QLabel,
    QToolBar,
    QVBoxLayout,
    QWidget
)

from database.database_manager import DatabaseManager


class ToolBar(QWidget):
    page_updated = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()

        self.db_manager = db_manager

        self.toolbar = QToolBar()

        self.current_page = 1

        # Previous Page Action
        prev_page_action = QAction("<", self)
        prev_page_action.triggered.connect(self.load_previous_page)
        self.toolbar.addAction(prev_page_action)

        # Current Page Label
        self.page_label = QLabel()
        self.update_page_label()
        self.toolbar.addWidget(self.page_label)

        # Next Page Action
        next_page_action = QAction(">", self)
        next_page_action.triggered.connect(self.load_next_page)
        self.toolbar.addAction(next_page_action)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)

        self.setLayout(layout)


    def update_page_label(self):
        self.page_label.setText(f"Page {self.current_page}")

    
    def load_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1

            self.page_updated.emit()

            self.update_page_label()


    def load_next_page(self):
        # Check if there are more pages
        more_pages = len(self.db_manager.search_images(list(), self.current_page+1)) > 0

        if more_pages:
            self.current_page += 1

            self.page_updated.emit()

            self.update_page_label()


    def reset_page(self):
        self.current_page = 1

        self.page_updated.emit()

        self.update_page_label()