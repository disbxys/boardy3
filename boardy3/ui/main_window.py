import os
from typing import Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget
)

from boardy3.database import column_to_int
from boardy3.database.database_manager import DatabaseManager
from boardy3.database.image_loader import ImageLoader, DirImageLoader, NetworkImageLoader
import boardy3.database.models as db_models
from boardy3.ui.image import ImageUrlInputDialog, ImageWidget
from boardy3.ui.layout import FlowLayout, clear_layout
from boardy3.ui.searchbox import SearchBox
from boardy3.ui.tag import BatchCreateTagsDialog
from boardy3.ui.toolbar import ToolBar


class MainWindow(QMainWindow):
    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__()

        self.db_manager = db_manager

        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()

        # Define an area to display images
        self.scroll_area = QScrollArea(self.central_widget)
        self.scroll_widget = QWidget(self.scroll_area)
        self.images_layout = FlowLayout(self.scroll_widget)

        # 
        self._create_actions()
        self._create_menu_bar()

        self.toolbar = ToolBar(db_manager)
        self.toolbar.page_updated.connect(self.refresh_images)

        self.searchbox = SearchBox(db_manager)
        self.searchbox.search_button.clicked.connect(self.search_images)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.searchbox)
        layout.addWidget(self.scroll_area)

        # central_widget = QWidget()
        self.central_widget.setLayout(layout)

        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.scroll_widget.setLayout(self.images_layout)

        self.setCentralWidget(self.central_widget)

        # Show all images on startup
        self.refresh_images()
    

    def _create_actions(self) -> None:
        self.import_action = QAction("Import Image(s)", self)
        self.import_action.triggered.connect(self.upload_images)
        self.import_action.setShortcut(QKeySequence("Ctrl+K"))

        self.web_import_action = QAction("Import from Web", self)
        self.web_import_action.triggered.connect(self.upload_web_images)
        self.web_import_action.setShortcut(QKeySequence("Ctrl+W"))

        self.import_dir_action = QAction("Import Folder", self)
        self.import_dir_action.triggered.connect(self.upload_images_from_dir)
        self.import_dir_action.setShortcut(QKeySequence("Ctrl+Shift+K"))

        self.batch_create_tags_action = QAction("Create Tags", self)
        self.batch_create_tags_action.triggered.connect(self.batch_create_tags)
        self.batch_create_tags_action.setShortcut(QKeySequence("Ctrl+B"))


    def _create_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

        # Import Menu
        import_menu = menu_bar.addMenu("File")
        import_menu.addAction(self.import_action)
        import_menu.addAction(self.web_import_action)
        import_menu.addAction(self.import_dir_action)
        import_menu.addAction(self.batch_create_tags_action)

        self.setMenuBar(menu_bar)

    
    def upload_images(self) -> None:
        file_dialogue = QFileDialog()
        file_paths, _ = file_dialogue.getOpenFileNames(
            self,
            "Open Image",
            "",
            "Image Files (*.bmp *.gif *.jpeg *.jpg *.png *.webp);;All Files (*)"
        )

        if file_paths:
            # Create a progress dialog to show the progress of image loading
            progress_dialog = QProgressDialog(
                "Importing Images...", "Cancel",
                0, len(file_paths)
            )
            progress_dialog.setWindowTitle("Importing Images")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)

            # Create an ImageLoader thread and connect signals
            image_loader = ImageLoader(self.db_manager, file_paths)
            image_loader.progress_updated.connect(progress_dialog.setValue)
            image_loader.finished.connect(progress_dialog.accept)

            # Hide the cancel button (until I can find a better way
            # to handle safely exiting the image loader thread)
            # (2024-03-27)
            # progress_dialog.findChildren(QPushButton)[0].hide()
            progress_dialog.canceled.connect(image_loader.terminate)    # The cancel button doesn't really work

            # Start the ImageLoader thread
            image_loader.start()

            # Display the progress dialog
            progress_dialog.exec()

            # Reset page back to 1
            # This should trigger a page refresh
            self.toolbar.reset_page()

    
    def upload_web_images(self) -> None:
        url_dialogue = ImageUrlInputDialog()
        # Grab the image urls
        url_dialogue.exec()

        image_urls = url_dialogue.image_urls

        if image_urls:
            # Create a progress dialog to show the progress of image loading
            progress_dialog = QProgressDialog(
                "Importing Images from Web...", "Cancel",
                0, len(image_urls)
            )
            progress_dialog.setWindowTitle("Importing Images From Web")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)

            # Create an ImageLoader thread and connect signals
            net_image_loader = NetworkImageLoader(self.db_manager, image_urls)
            net_image_loader.progress_updated.connect(progress_dialog.setValue)
            net_image_loader.finished.connect(progress_dialog.accept)

            # Hide the cancel button (until I can find a better way
            # to handle safely exiting the image loader thread)
            # (2024-03-27)
            # progress_dialog.findChildren(QPushButton)[0].hide()
            progress_dialog.canceled.connect(net_image_loader.terminate)    # The cancel button doesn't really work

            # Start the ImageLoader thread
            net_image_loader.start()

            # Display the progress dialog
            progress_dialog.exec()

            # Reset page back to 1
            # This should trigger a page refresh
            self.toolbar.reset_page()

    
    def upload_images_from_dir(self) -> None:
        dir_dialogue = QFileDialog()
        dir_path = dir_dialogue.getExistingDirectory(
            self,
            "Open Folder",
            ""
        )

        if os.path.exists(dir_path):
            # Create a progress dialog to show the progress of image loading
            progress_dialog = QProgressDialog(
                "Importing Images...", "Cancel",
                0, 1
            )
            progress_dialog.setWindowTitle("Importing Images")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)

            # Create an DirImageLoader thread and connect signals
            dir_image_loader = DirImageLoader(self.db_manager, dir_path)
            dir_image_loader.progress_updated.connect(progress_dialog.setValue)
            dir_image_loader.finished.connect(progress_dialog.accept)
            # Change max value in progress dialog
            dir_image_loader.scan_completed.connect(progress_dialog.setMaximum)

            # I have no idea why this started working properly.
            # Just gonna assume it barrel magic. (2024-04-25)
            progress_dialog.canceled.connect(dir_image_loader.terminate)

            # Start the ImageLoader thread
            dir_image_loader.start()

            # Display the progress dialog
            progress_dialog.exec()

            # Reset page back to 1
            # This should trigger a page refresh
            self.toolbar.reset_page()
    

    def batch_create_tags(self) -> None:
        # Instance BatchCreateTagsDialog
        batch_create_dialog = BatchCreateTagsDialog()
        batch_create_dialog.exec()

        
    def search_images(self) -> None:
        tags_string = self.searchbox.search_line_edit.text().strip()
        image_results = self.db_manager.search_images(
            tags_string.split(),
            page=1,
            page_size=int(self.toolbar.page_size_combo_box.currentText())
        )

        # Reset page back to 1
        self.toolbar.reset_page()
        # FIXME: This is not optimal since the page gets refreshed before
        # clearing the layout again.
        # Clear existing widgets from layout
        self.clear_images_layout()

        # Re-populate images layout with update list of images
        self._add_images_to_layout(image_results)

    
    def refresh_images(self) -> None:
        # Clear existing widgets from layout
        self.clear_images_layout()

        # Re-populate images layout with update list of images
        # The empty list is there as a janky fix until I find a
        # better solution (2024-02-08).
        images = self.db_manager.search_images(
            list(),
            self.toolbar.current_page,
            int(self.toolbar.page_size_combo_box.currentText())
        )

        self._add_images_to_layout(images)
    

    def clear_images_layout(self) -> None:
        clear_layout(self.images_layout)

    
    def _add_image_to_layout(self, image: db_models.Image) -> None:
        image_widget = self._create_image_widget(column_to_int(image.id))
        self.images_layout.addWidget(image_widget)


    def _add_images_to_layout(self, images: Sequence[db_models.Image]) -> None:
        for image in images:
            self._add_image_to_layout(image)
    

    def _create_image_widget(
            self,
            db_id: int
    ) -> ImageWidget:
        image_ = ImageWidget(db_id, 250, 250)
        # Refresh gallery after deleting widget
        image_.deleted.connect(self.refresh_images)
        return image_
    

    # Quit the application when the main window is closed
    def closeEvent(self, event: QCloseEvent) -> None:
        QApplication.quit()
