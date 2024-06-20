
import re
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QStringListModel
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget
)

from boardy3.database import column_to_int
from boardy3.database.database_manager import DatabaseItemDoesNotExist, DatabaseItemExists, DatabaseManager
from boardy3.database.models import Tag
from boardy3.ui.layout import FlowLayout, clear_layout, iterate_layout
from boardy3.utils import get_logger


logger = get_logger(__name__)


class TagWidget(QWidget):
    def __init__(self, tag: Tag):
        super().__init__()

        self.tag_id = str(tag.id)
        self.tag_name = str(tag.name)
        # The number of images that contain the tag
        self.image_count = len(tag.images)

        self.checkbox = QCheckBox()
        self.tag_description = QLabel(f"{self.tag_name} ({self.image_count})")

        layout = QHBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.tag_description)

        self.setLayout(layout)


class TagsWindow(QWidget):
    """A class for displaying an image's tag(s)"""

    def __init__(
            self,
            image_id: int,
            db_manager: DatabaseManager | None = None,
            portrait: bool = False
    ):
        super().__init__()

        self.db_manager = db_manager or DatabaseManager()
        self.image_id = image_id

        # Define an area to display tags
        self.tags_scroll_area = QScrollArea(self)
        self.tags_scroll_widget = QWidget(self.tags_scroll_area)
        self.tags_list_layout = FlowLayout(self.tags_scroll_widget)

        self.remove_tag_button = QPushButton("Remove")
        self.remove_tag_button.clicked.connect(self._remove_tags)

        # Create a checkbox to switch between removing tags from an image
        # and deleting tags.
        self.delete_tag_checkbox = QCheckBox("Delete")
        
        # Display image tags
        self.refresh_tags_list()

        # Set scroll area properties
        self.tags_scroll_area.setWidgetResizable(True)
        self.tags_scroll_area.setWidget(self.tags_scroll_widget)
        if portrait:
            self.setFixedWidth(200)
            self.tags_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setFixedHeight(200)
            self.tags_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Setup a tag input box for adding/creating new tags
        self.tag_input = TagInsertBox(self.image_id, self.db_manager)
        self.tag_input.tag_added.connect(self.refresh_tags_list)

        layout = QVBoxLayout()
        layout.addWidget(self.tags_scroll_area)
        layout.addWidget(self.tag_input)
        layout.addWidget(self.remove_tag_button)
        layout.addWidget(self.delete_tag_checkbox)

        self.setLayout(layout)


    def refresh_tags_list(self):
        if self.tags_list_layout.count() > 0:
            clear_layout(self.tags_list_layout)

        for tag in self.db_manager.get_tags_by_image_id(self.image_id):
            self.tags_list_layout.addWidget(TagWidget(tag))

        
    @pyqtSlot()
    def _remove_tags(self):
        checked_tags = self._gather_checked_tags()

        msg_box = QMessageBox()

        match self.delete_tag_checkbox.checkState():
            case Qt.CheckState.Checked:     # Delete Tag
                answer = msg_box.question(
                    self,
                    "Delete Tag Confirmation",
                    "Delete the selected tags from the database?",
                    msg_box.StandardButton.Yes | msg_box.StandardButton.No
                )

                if answer == msg_box.StandardButton.Yes:
                    self.db_manager.delete_tags(
                        [int(tag.tag_id) for tag in checked_tags]
                    )

                    # Reset delete tag checkbox to unchecked state
                    self.delete_tag_checkbox.setCheckState(Qt.CheckState.Unchecked)

            case Qt.CheckState.Unchecked:   # Remove tag from image
                answer = msg_box.question(
                    self,
                    "Remove Tag Confirmation",
                    "Remove the selected tags from the image?",
                    msg_box.StandardButton.Yes | msg_box.StandardButton.No
                )

                if answer == msg_box.StandardButton.Yes:
                    logger.info(
                        "Tags removed from image: {}"\
                        .format(" ".join([tag.tag_name for tag in checked_tags]))
                    )
                    
                    self.db_manager.remove_tags_from_image(
                        [int(tag.tag_id) for tag in checked_tags],
                        self.image_id
                    )

                    # Reset delete tag checkbox to unchecked state
                    self.delete_tag_checkbox.setCheckState(Qt.CheckState.Unchecked)
            case _:
                # This should never get here
                raise Exception("Unknown check state detected.")

        self.refresh_tags_list()

    
    def _gather_checked_tags(self) -> list[TagWidget]:
        checked_tags: list[TagWidget] = []
        for tag in iterate_layout(self.tags_list_layout):
            if isinstance(tag, TagWidget):
                if tag.checkbox.isChecked():
                    checked_tags.append(tag)
        
        return checked_tags


class TagInsertBox(QWidget):
    """A class for handling adding new tags"""
    tag_added = pyqtSignal()

    def __init__(
            self,
            image_id: int,
            db_manager: DatabaseManager
    ):
        super().__init__()

        self.db_manager = db_manager
        self.image_id = image_id

        # TODO: Add placeholder w/ instructions to split tags by comma
        self.input_box = QLineEdit()
        self.input_box.returnPressed.connect(self.on_return_pressed)

        # Create a QCompleter for input box
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.input_box.setCompleter(self.completer)
        # Initialize a Completer Model to pair with QCompleter
        self.completer_model = QStringListModel()

        self.input_box.textChanged.connect(self.fetch_and_update_completer)

        layout = QHBoxLayout()
        layout.addWidget(self.input_box)

        self.setLayout(layout)


    def fetch_and_update_completer(self):
        # Remove any trailing whitespace
        search_text = self.input_box.text().strip()

        # Do not search for tags if searchline is empty
        # TODO: Maybe create a custom Completer if handle these cases
        if search_text != "":
            search_terms = self._fetch_search_terms(search_text)
            self.completer_model.setStringList(search_terms)
            self.completer.setModel(self.completer_model)


    def _fetch_search_terms(self, text: str) -> list[str]:
        search_terms = self.db_manager.search_tags(text)
        return [str(search_term.name) for search_term in search_terms]

    
    def on_return_pressed(self):
        # Verify image id
        image = self.db_manager.get_image(self.image_id)
        if image is None:
            raise DatabaseItemDoesNotExist(f"Image id <{self.image_id}> does not exist.")

        # Parse input into tags
        tags_input = self.input_box.text().split(",")
        for tag_name in tags_input:
            tag_name = re.sub(r"\s", "_", tag_name.strip())

            if tag_name:    # Skip empty names
                # Try adding tag to db if new else get tag from db
                tag = self.db_manager.get_tag_by_name(tag_name)
                if tag is None:
                    tag = self.db_manager.add_tag(tag_name)

                tag_newly_added = self.db_manager.add_tag_to_image(tag, column_to_int(image.id))

                # Clear input box at the end
                self.input_box.clear()

                if tag_newly_added:
                    self.tag_added.emit()


class BatchCreateTagsDialog(QDialog):
    def __init__(
            self,
            parent: QWidget | None = None,
            db_manager: DatabaseManager | None = None
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Enter Tags")

        self.db_manager = db_manager or DatabaseManager()

        self.input_box_label = QLabel("One tag per line:")
        self.input_box = QPlainTextEdit()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.on_save)

        layout = QVBoxLayout()
        layout.addWidget(self.input_box_label)
        layout.addWidget(self.input_box, stretch=1)
        layout.addWidget(self.save_button)

        self.setLayout(layout)


    @pyqtSlot()
    def on_save(self):
        added_tags = list()

        tag_names = self._parse_input()
        for tag_name in tag_names:
            try:
                _tag = self.db_manager.add_tag(tag_name)
                added_tags.append(_tag)
            except DatabaseItemExists:
                pass
        
        logger.info(f"Number of tags saved: {len(added_tags)}.")

        self.close()


    def _parse_input(self) -> list[str]:
        """
        Parse text from input box and return a list of
        non-empty strings.
        """

        input_text = self.input_box.toPlainText()

        if len(input_text.strip("\n")) == 0:
            return list()
        
        tokens = list()
        for token in input_text.split("\n"):
            if token != "":
                # Remove trailing/leading whitespace and replace
                # all other whitespace with underline (_)
                cleaned_token = re.sub(r"\s{1,}", "_", token.strip())
                tokens.append(cleaned_token)

        return tokens