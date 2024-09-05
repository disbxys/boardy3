import os
import sys

from PyQt6.QtWidgets import QApplication

from boardy3.database.database_manager import DatabaseManager
from boardy3.ui.main_window import MainWindow


def launch_app():
    # Add dll to PATH before running code
    dll_directory = os.path.abspath("bin")
    os.environ["PATH"] = dll_directory + os.pathsep + os.environ["PATH"]

    app = QApplication(sys.argv)

    db_manager = DatabaseManager()
    main_win = MainWindow(db_manager)
    main_win.show()

    sys.exit(app.exec())