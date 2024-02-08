from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QVBoxLayout,
    QWidget
)

class SearchBox(QWidget):
    def __init__(self):
        super().__init__()

        self.search_line_edit = QLineEdit()
        self.search_button = QPushButton("Search")

        layout = QHBoxLayout()
        layout.addWidget(self.search_line_edit)
        layout.addWidget(self.search_button)


        self.setLayout(layout)

        # TODO: implement search by tag