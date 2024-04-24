from PyQt6.QtCore import pyqtSlot, Qt, QTimer, QStringListModel
from PyQt6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget
)

from database.database_manager import DatabaseManager

class SearchBox(QWidget):
    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__()

        self.db_manager = db_manager

        self.search_line_edit = QLineEdit()
        self.search_button = QPushButton("Search")

        # Create a QCompleter for searchline
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.search_line_edit.setCompleter(self.completer)
        # Initialize a Completer Model to pair with QCompleter
        self.completer_model = QStringListModel()

        self.search_line_edit.textChanged.connect(self.featch_and_update_completer)

        layout = QHBoxLayout()
        layout.addWidget(self.search_line_edit)
        layout.addWidget(self.search_button)

        self.setLayout(layout)


    @pyqtSlot()
    def _update_completer(self, text):
        """Restart the timer when text changes"""
        self.timer.start(500)

    
    def featch_and_update_completer(self):
        search_text = self.search_line_edit.text().strip()

        # Do not search for tags if searchline is empty
        if search_text != "":
            search_terms = self._fetch_search_terms(search_text)
            self.completer_model.setStringList(search_terms)
            self.completer.setModel(self.completer_model)


    def _fetch_search_terms(self, text: str) -> list[str]:
        search_terms = self.db_manager.search_tags(text)
        return [str(search_term.name) for search_term in search_terms]
