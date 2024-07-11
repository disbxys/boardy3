import logging
import random
import os
import unittest

from boardy3.database.image_loader import is_image


class TestMediaFile(unittest.TestCase):

    def setUp(self) -> None:
        # Disable logging during testing
        logging.disable(logging.ERROR)

        self.test_images_with_correct_extensions = [
            os.path.join(os.getcwd(), "tests/static/images", "test_image1.jpeg"),
            os.path.join(os.getcwd(), "tests/static/images", "test_image2.jpg"),
        ]
        self.test_images_with_incorrect_extensions = [
            os.path.join(os.getcwd(), "tests/static/images", "image_with_incorrect_image_extension.png"),
            os.path.join(os.getcwd(), "tests/static/images", "image_with_no_extension")
        ]

        self.test_videos = [
            os.path.join(os.getcwd(), "tests/static/videos", "stock_video1.mp4"),
            os.path.join(os.getcwd(), "tests/static/videos", "stock_video2.webm"),
            os.path.join(os.getcwd(), "tests/static/videos", "stock_video2.mp4")
        ]

        return super().setUp()


    def test_is_image_with_correct_extension(self):
        self.assertTrue(all(
            is_image(test_image) for test_image in self.test_images_with_correct_extensions
        ))

    
    def test_is_image_with_incorrect_extension(self):
        self.assertTrue(all(
            is_image(test_image) for test_image in self.test_images_with_incorrect_extensions
        ))


    def test_is_not_image(self):
        self.assertTrue(all(
            is_image(test_video)==False for test_video in self.test_videos
        ))