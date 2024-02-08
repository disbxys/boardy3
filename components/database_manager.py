from fileinput import filename
import hashlib
import os
import shutil
from typing import List, Optional, Sequence

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, Session

from models import Base, Image, image_tag, Tag


class DatabaseException(Exception):
    """Base class for database exceptions."""
    pass


class DatabaseItemExists(DatabaseException):
    """
    Exception class for when attempting to created an item when it
    already exists in the database.
    """



class DatabaseManager:
    def __init__(self):
        self.engine = create_engine("sqlite:///image_database.db", echo=False)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.image_dir_path = os.path.join(os.getcwd(), "db", "image_files")

    
    def add_image(self, filepath, tags=None):
        # Calculate file hash to use as new filename
        image_hash = self._sha256_hash_image_data(filepath)
        
        base_filename = os.path.basename(filepath)  # Strip parents
        file_stem, file_ext = os.path.splitext(base_filename)
        # Handle edgecase such as '.jpg' as the entire filename
        if file_ext == "":
            file_ext = file_stem

        # Create new filename using file hash and keep extension
        new_filename = image_hash + file_ext

        # Create a save path based on file hash
        image_dir = self._get_image_dir(image_hash)
        save_path = os.path.join(image_dir, new_filename)

        # Do not process images already saved or duplicates
        # It should be safe to assume that if the image does not
        # exist in the file system then it also should not exist
        # in the database. Therefore, we do not need to worry about
        # UNIQUE filename constraint errors.
        if os.path.exists(save_path):
            raise DatabaseItemExists(f"<{new_filename}>")
        
        # Save image to filesystem
        os.makedirs(image_dir, exist_ok=True)
        shutil.copy(filepath, save_path)

        # Create new Image record
        new_image = Image(filename=new_filename)

        if not tags: tags = list()
        for tag_name in tags:
            tag = self.session.query(Tag).filter_by(name=tag_name).first()

            if not tag:
                tag = Tag(name=tag_name)
                self.session.add(tag)

            new_image.tags.append(tag)

        self.session.add(new_image)
        self.session.commit()


    def get_image(self, id: int) -> Optional[Image]:
        return Image.query.filter_by(id=id).first()


    def get_all_images(self, newest_first: bool = False) -> List[Image]:
        query = self.session.query(Image)
        if newest_first:
            query = query.order_by(Image.id.desc())
        else:
            query = query.order_by(Image.id)

        return query.all()


    def search_images(self, tags_list: List[str]) -> List[Image]:
        # Filter out invalid tags
        tags = self.session.query(Tag).filter(Tag.name.in_(tags_list)).all()

        if (len(tags_list) != 0) and (len(tags) == 0):
            # Non-empty tags list and no valid tags where found
            query = self.session.query(Image).filter_by(id=None)
        else:
            # Create the start of the search query string
            query = self.session.query(Image)

            # I had to separate this from the initial query because SQLAlchemy
            # apparently doesn't like it when there are joins without a WITH
            # clause.
            if len(tags) != 0:
                query = query.join(image_tag, image_tag.c.image_id == Image.id)\
                    .join(Tag, Tag.id == image_tag.c.tag_id)

            # Add an AND = clause for each tag
            for tag in tags:
                query = query.filter(Tag.name == tag.name)

        return query.order_by(Image.id.desc()).all()
    

    def get_image_path(self, filename: str) -> str:
        return os.path.normpath(os.path.join(
            self._get_image_dir(filename),
            filename
        ))


    def _get_image_dir(self, filename: str) -> str:
        return os.path.normpath(os.path.join(
            self.image_dir_path,
            f"{filename[:2]}/{filename[2:4]}"
        ))
    

    def _sha256_hash_image_data(self, filepath: str) -> str:
        with open(filepath, "rb") as infile:
            return hashlib.sha256(infile.read()).hexdigest()


if __name__ == "__main__":
    db = DatabaseManager()

    # db.add_image(
    #     filepath="sample_image.jpeg",
    #     tags=["black_and_white"]
    # )

    for item in db.get_all_images():
        print(f"{item.id} | {item.filename} " + ";".join(t.name for t in item.tags))