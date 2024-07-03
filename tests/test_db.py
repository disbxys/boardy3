import os
import random
import shutil
import unittest

from boardy3.database.database_manager import DatabaseManager
import boardy3.database.exceptions as db_exc
from boardy3.database.models import Image


class TestDB(unittest.TestCase):
    
    def setUp(self) -> None:
        self.db_manager = DatabaseManager(is_test=True)

        self.test_images = [
            os.path.join(os.getcwd(), "tests/static/images", "test_image1.jpeg"),
            os.path.join(os.getcwd(), "tests/static/images", "test_image2.jpg")
        ]

        return super().setUp()
    

    def test_insert_image(self):
        # Get a random test image
        _image = random.choice(self.test_images)

        # Add image to database
        self.db_manager.add_image(_image)

        # Grab newly added image
        db_image = self.db_manager.get_all_images(newest_first=True)[0]
        db_image_path = self.db_manager.get_image_path(db_image.filename)

        # Test image in database has a copy of the image in image directory
        self.assertTrue(os.path.exists(db_image_path))

        # Test image hash matches db image hash
        image_hash = self.db_manager.sha256_hash_image_data(db_image_path)
        db_image_hash = self.db_manager.sha256_hash_image_data(db_image_path)
        self.assertEqual(image_hash, db_image_hash)

    
    def test_delete_image(self):
        for image_path in self.test_images:
            self.db_manager.add_image(image_path)

        # Grab random image record from db
        db_image = random.choice(self.db_manager.get_all_images())

        self.db_manager.delete_image(db_image.id)

        self.assertIsNone(self.db_manager.get_image(db_image.id))

    
    def test_delete_all_images(self):
        self.db_manager.delete_all_images()

        self.assertEqual(
            len(self.db_manager.get_all_images()),
            0,
            "Not all images have been deleted from the database."
        )

        image_files = [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(self.db_manager.image_dir_path)
            for filename in filenames
        ]

        self.assertEqual(
            len(image_files),
            0,
            "Not all image files have been deleted."
        )
    

    def tearDown(self) -> None:
        # Clear all images and tags from database
        self.db_manager.delete_all_tags()
        self.db_manager.delete_all_images()

        # Clear all images from image directory
        if os.path.exists(self.db_manager.image_dir_path):
            shutil.rmtree(self.db_manager.image_dir_path)

        return super().tearDown()
