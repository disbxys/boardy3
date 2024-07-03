import logging
import os
import random
import shutil
import unittest

from boardy3.database.database_manager import DatabaseManager


class TestDB(unittest.TestCase):
    
    def setUp(self) -> None:
        # Disable logging during testing
        logging.disable(logging.ERROR)

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

    
    def test_add_tag(self):
        tag_name = "test_tag"

        tag_ = self.db_manager.add_tag(tag_name)

        self.assertIsNotNone(tag_)
        self.assertIsNotNone(self.db_manager.get_tag_by_name(tag_name))


    def test_fail_add_existing_tag(self):
        raise NotImplementedError


    def test_add_tag_to_image(self):
        # Get a random test image
        _image = random.choice(self.test_images)

        # Add image to database
        self.db_manager.add_image(_image)

        # Grab newly added image
        db_image = self.db_manager.get_all_images(newest_first=True)[0]
        db_image_path = self.db_manager.get_image_path(db_image.filename)

        # Create a test tag
        tag_ = self.db_manager.add_tag("test_tag")

        # Test if tag successfully added to image
        self.assertTrue(self.db_manager.add_tag_to_image(tag_, db_image.id))

        # Try getting newly added image after adding tag to image
        test_db_image = self.db_manager.get_all_images(newest_first=True)[0]
        test_db_image_path = self.db_manager.get_image_path(db_image.filename)

        # Just checking for peace of mind if db_image is the same image from
        # before adding the tag to it (aside from the state of its tags).
        self.assertEqual(
            db_image.id, test_db_image.id,
            "Image was some how changed from adding tag to image."
        )
        self.assertEqual(
            db_image.filename, test_db_image.filename,
            "Image was some how changed from adding tag to image."
        )
        self.assertEqual(
            db_image_path, test_db_image_path,
            "Image was some how changed from adding tag to image."
        )

        self.assertTrue(tag_ in test_db_image.tags, f"Tag has not been added to test image.")

    
    def test_add_tags_to_image(self):
        raise NotImplementedError
    

    def test_fail_add_tag_to_nonexisting_image(self):
        raise NotImplementedError
    

    def test_delete_tag(self):
        raise NotImplementedError
    

    def test_delete_nonexisting_tag(self):
        raise NotImplementedError
    

    def test_delete_all_tags(self):
        raise NotImplementedError
    

    def test_remove_tag_from_image(self):
        raise NotImplementedError
    

    def test_remove_tags_from_image(self):
        raise NotImplementedError
    

    def tearDown(self) -> None:
        # Clear all images and tags from database
        self.db_manager.delete_all_tags()
        self.db_manager.delete_all_images()

        # Clear all images from image directory
        if os.path.exists(self.db_manager.image_dir_path):
            shutil.rmtree(self.db_manager.image_dir_path)

        self.db_manager.session.close()

        # Re-enable logging after running all tests
        logging.disable(logging.NOTSET)

        return super().tearDown()
