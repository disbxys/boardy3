import os
from typing import Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget
)
from sqlalchemy import Column

from database.database_manager import DatabaseManager
from database.image_loader import ImageLoader, DirImageLoader
import database.models as db_models
from ui.layouts import FlowLayout
from ui.searchbox import SearchBox
from ui.toolbar import ToolBar


class MainWindow(QMainWindow):
    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__()

        self.db_manager = db_manager

        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 800, 800)

        self.central_widget = QWidget()

        # Define an area to display images
        self.scroll_area = QScrollArea(self.central_widget)
        self.scroll_widget = QWidget(self.scroll_area)
        self.images_layout = FlowLayout(self.scroll_widget)

        # Button for importing multiple images
        upload_images_button = QPushButton("Upload Images", self)
        upload_images_button.clicked.connect(self.upload_images)

        # Button for recursively importing images from a selected directory
        upload_image_dir_button = QPushButton("Upload Folder (Recursive)", self)
        upload_image_dir_button.clicked.connect(self.upload_images_from_dir)

        self.toolbar = ToolBar(db_manager)
        self.toolbar.page_updated.connect(self.refresh_images)

        self.searchbox = SearchBox()
        self.searchbox.search_button.clicked.connect(self.search_images)
        # TODO: Remove this line after tagging is properly implemented
        self.searchbox.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.searchbox)
        layout.addWidget(self.scroll_area)
        layout.addWidget(upload_images_button)
        layout.addWidget(upload_image_dir_button)

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
                "Uploading Images...", "Cancel",
                0, len(file_paths)
            )
            progress_dialog.setWindowTitle("Uploading Images")
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
                "Uploading Images...", "Cancel",
                1, 1
            )
            progress_dialog.setWindowTitle("Uploading Images")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)

            # Create an ImageLoader thread and connect signals
            image_loader = DirImageLoader(self.db_manager, dir_path)
            # image_loader.progress_updated.connect(progress_dialog.setValue)
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

        
    
    def search_images(self) -> None:
        tags_string = self.searchbox.search_line_edit.text().strip()
        image_results = self.db_manager.search_images(tags_string.split(),
            page=1
        )

        # Reset page back to 1
        self.toolbar.reset_page()
        
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
        images = self.db_manager.search_images(list(), self.toolbar.current_page)

        self._add_images_to_layout(images)
    

    def clear_images_layout(self) -> None:
        for i in reversed(range(self.images_layout.count())):
            widget = self.images_layout.itemAt(i)
            if widget:
                widget = widget.widget()
                widget.setParent(None)

    
    def _add_image_to_layout(self, image: db_models.Image) -> None:
        image_widget = self._create_image_widget(image.filename)
        self.images_layout.addWidget(image_widget)


    def _add_images_to_layout(self, images: Sequence[db_models.Image]) -> None:
        for image in images:
            self._add_image_to_layout(image)
    

    def _create_image_widget(self, filename: str | Column[str]) -> QWidget:
        image_widget = QLabel(self)
        image_path = self.db_manager.get_image_path(filename)
        pixmap = QPixmap(image_path)

        image_widget.setPixmap(pixmap.scaled(
            250, 250,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

        return image_widget