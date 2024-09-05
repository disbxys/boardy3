import os
import re

# # Add dll to PATH before running code
# dll_directory = os.path.abspath("bin")
# os.environ["PATH"] = dll_directory + os.pathsep + os.environ["PATH"]
# import mpv

import cv2
from PyQt6.QtCore import pyqtSignal, Qt, QUrl, QSize
from PyQt6.QtGui import QMouseEvent, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget
)

from boardy3.database.database_manager import DatabaseManager
from boardy3.database.models import Tag


class VideoPlayerWidget(QWidget):

    def __init__(
            self,
            db_id: int=0,
            width: int | None = None,
            height: int | None = None,
            db_manager: DatabaseManager | None = None,
            video_path = ""
    ):
        super().__init__()

        # Video id from database
        self.db_id = db_id
        
        self.db_manager = db_manager or DatabaseManager()

        # Grab video from database
        self.video_ = self.db_manager.get_image(self.db_id)
        if self.video_ is None:
            raise ValueError(f"Invalid video id: {self.db_id}.")

        self.video_path = self.db_manager.get_image_path(self.video_.filename)

        self.layout_ = QVBoxLayout()

        # Video container
        self.video_container = QVideoWidget()
        self.video_width = 0
        self.video_height = 0

        # Audio output
        self.audio_output = QAudioOutput()

        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_container)
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(self.video_path))

        # Button to play video
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_video)

        # Button to stop video
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_video)

        # Define media controls widget
        self.media_control_widget = QWidget()
        self.media_control_layout = QHBoxLayout()
        self.media_control_layout.addWidget(self.play_button)
        self.media_control_layout.addWidget(self.stop_button)
        self.media_control_widget.setLayout(self.media_control_layout)

        self.resize_video_widget()

        self.layout_.addWidget(self.video_container)
        self.layout_.addWidget(self.media_control_widget)

        self.setLayout(self.layout_)

        # # Media Player
        # self.player = mpv.MPV(
        #     wid=str(int(self.container.winId())),
        #     vo="x11",
        #     input_vo_keyboard=True
        # )

        # # Set the media
        # self.player.observe_property("width", self.update_video_dimensions)
        # self.player.observe_property("height", self.update_video_dimensions)


    def play_video(self):
        self.player.play()
    

    def stop_video(self):
        self.player.stop()

    
    # def get_width(self):
    #     width = self.video_widget.width()
    #     height = self.video_widget.height()
    #     print(width, height)

        # return self.media_player.metaData(QMediaPlayer.MediaStatus.)


    # def update_video_dimensions(self, name, value):
    #     if name == "width" or name == "hieght":
    #         width = self.player.properties["width"]
    #         height = self.player.properties["height"]

    #         if width and height:
    #             self.dimensions_label.setText(f"Video Dimensions: {width}x{height}")
    #             self.resize_video_widget(1200, 700)


    def resize_video_widget(self):
        aspect_ratio = 1

        width, height = self.get_video_dimensions()

        new_width = width
        new_height = int(width / aspect_ratio)

        if new_height > height:
            new_height = height
            new_width = int(new_height * aspect_ratio)

        self.setFixedSize(QSize(new_width, new_height))

    
    def get_video_dimensions(self) -> tuple[int, int]:
        cap = cv2.VideoCapture(self.video_path)
        self.video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cap.release()

        return self.video_width, self.video_height
    

    def fetch_tags(self) -> list[Tag]:
        return self.db_manager.get_tags_by_image_id(self.db_id)
    

    def delete_image(self) -> None:
        self.db_manager.delete_image(self.db_id)
    

    def get_width(self) -> int:
        return self.video_width
    

    def get_height(self) -> int:
        return self.video_height
