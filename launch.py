import sys

from PyQt6.QtWidgets import QApplication

from database.database_manager import DatabaseManager
from ui.main_window import MainWindow


def launch_app():
    app = QApplication(sys.argv)

    db_manager = DatabaseManager()
    main_win = MainWindow(db_manager)
    main_win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch_app()
