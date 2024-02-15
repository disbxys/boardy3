from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget
)

class SearchBox(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.search_line_edit = QLineEdit()
        self.search_button = QPushButton("Search")

        layout = QHBoxLayout()
        layout.addWidget(self.search_line_edit)
        layout.addWidget(self.search_button)


        self.setLayout(layout)