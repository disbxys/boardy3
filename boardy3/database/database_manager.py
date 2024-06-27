import hashlib
import os
import shutil
from typing import Optional

from sqlalchemy import create_engine, Column, exc
from sqlalchemy.orm import Session

from boardy3.database.exceptions import DatabaseItemDoesNotExist, DatabaseItemExists
from boardy3.database.models import Base, Image, image_tag, Tag
from boardy3.utils import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    DEFAULT_PAGE_SIZE = 20

    def __init__(self) -> None:
        db_instance_dirpath = "instance"
        os.makedirs(db_instance_dirpath, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_instance_dirpath}/image_database.db", echo=False)

        Base.metadata.create_all(self.engine)

        self.session = Session(self.engine)

        self.image_dir_path = os.path.join(
            os.getcwd(), "db", "image_files"
        )
        os.makedirs(self.image_dir_path, exist_ok=True)

    
    def add_image(self, filepath: str, tags: list[str] | None = None) -> None:
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

        try:
            if not tags: tags = list()
            for tag_name in tags:
                tag = self.session\
                    .query(Tag)\
                    .filter_by(name=tag_name)\
                    .first()

                if not tag:
                    tag = Tag(name=tag_name)
                    self.session.add(tag)

                new_image.tags.append(tag)

            self.session.add(new_image)
            self.session.commit()
        except exc.IntegrityError as e:
            # Delete image file since it was not added to the db.
            if os.path.exists(save_path):
                os.remove(save_path)

            # Re-raise exception
            raise e
    

    def delete_image(self, id: int) -> None:
        image_ = self.get_image(id)
        if image_ is None:
            raise DatabaseItemDoesNotExist(f"Image id: {id} does not exist.")
        
        # Delete image from database
        self.session.delete(image_)
        self.save()

        image_path = self.get_image_path(image_.filename)
        # By design, the image file should exist if it had existed in the
        # database unless the image location was tampered with.
        assert os.path.exists(image_path) == True
        # Delete physical file
        os.remove(image_path)

        logger.info(f"Image id deleted from database: {image_.id}")


    def get_image(self, id: int) -> Optional[Image]:
        return self.session.query(Image).filter_by(id=id).first()


    def get_all_images(self, newest_first: bool = False) -> list[Image]:
        query = self.session.query(Image)
        if newest_first:
            query = query.order_by(Image.id.desc())
        else:
            query = query.order_by(Image.id)

        return query.all()
    

    def get_images_count(self) -> int:
        """Return the number of image records in the database."""
        return self.session.query(Image).count()


    def search_images(
            self,
            tags_list: list[str],
            page: int,
            page_size: int = DEFAULT_PAGE_SIZE
    ) -> list[Image]:
        # Filter out invalid tags
        tags = self.session\
            .query(Tag)\
            .filter(Tag.name.in_(tags_list))\
            .all()
        
        # Set page size to default size if page size is not
        # a positive non-zero int.
        if page_size <= 0:
            page_size = self.DEFAULT_PAGE_SIZE

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
                query = query\
                    .join(image_tag, image_tag.c.image_id == Image.id)\
                    .join(Tag, Tag.id == image_tag.c.tag_id)

            # Add an AND = clause for each tag
            for tag in tags:
                query = query.filter(Tag.name == tag.name)


        # Calculate offset based on page number
        offset = (page - 1) * page_size

        return query\
            .order_by(Image.id.desc())\
            .offset(offset).limit(page_size)\
            .all()
    

    def get_tags_by_image_id(self, id: int | Column[int]) -> list[Tag]:
        return self.session.query(Tag)\
            .join(image_tag, image_tag.c.tag_id == Tag.id)\
            .join(Image, Image.id == image_tag.c.image_id)\
            .filter(image_tag.c.image_id == id)\
            .all()
    

    def get_tag_by_name(self, name: str | Column[str]) -> Tag | None:
        return self.session.query(Tag)\
            .filter_by(name=name)\
            .first()
    

    def add_tag(self, name: str) -> Tag:
        """
        Create a new Tag with the given name to the db.

        Returns the newly created tag.

        Raises DatabaseItemExists if a tag with the same
        name exists
        """
        tag = self.get_tag_by_name(name)
        if tag is not None:
            raise DatabaseItemExists(f"Tag <{tag.name}> already exists in database.")
        
        tag = Tag(name=name)

        self.session.add(tag)
        self.save()

        # Attempt to grab newly created tag
        new_tag = self.get_tag_by_name(tag.name)
        if new_tag is None:
            raise DatabaseItemDoesNotExist(f"Tag <{tag.name}> does not exist.")

        logger.info(f"New tag created: <{new_tag.id}> | <{new_tag.name}>.")
    
        return self.get_tag_by_name(name)
    

    def add_tag_to_image(self, tag: Tag, image_id: int) -> bool:
        # Verify image id
        if image:= self.get_image(image_id):
            # Verify the tag exists
            if self.get_tag_by_name(tag.name) is None:
                raise DatabaseItemDoesNotExist(f"Tag <{tag.name}> does not exist.")

            # Add tag to image if not on image already.
            if tag not in image.tags:
                image.tags.append(tag)
                logger.info(f"Added tag <{tag.name}> to image <{image.id}>.")

                self.save()
                return True
            else:
                logger.info(f"Tag <{tag.name}> already exists for image <{image_id}>.")
                return False
        
        raise DatabaseItemDoesNotExist(f"Image id <{image_id}> does not exist.")

    
    def remove_tag_from_image(self, tag_id: int, image_id: int):
        self.remove_tags_from_image([tag_id], image_id)

    
    def remove_tags_from_image(self, tag_ids: list[int], image_id: int):
        tags = self.session.query(Tag)\
            .filter(Tag.id.in_(tag_ids))\
            .all()
        
        image = self.get_image(image_id)

        if image and len(tags) > 0:
            image.remove_tags(tags)

            logger.info(
                "Tags removed from image id <{}>: {}".format(
                    image.id,
                    " ".join([str(tag.name) for tag in tags])
                )
            )

            self.save()


    def delete_tag(self, tag_id: int):
        self.delete_tags([tag_id])
    

    def delete_tags(self, tag_ids: list[int]):
        tags = self.session.query(Tag)\
            .filter(Tag.id.in_(tag_ids))\
            .all()
        
        for tag in tags:
            self.session.delete(tag)

        self.save()

        logger.info(
            "Tags deleted from database: {}"\
            .format(" ".join([str(tag.name) for tag in tags]))
        )


    def save(self):
        self.session.commit()


    def search_tags(self, keyword: str) -> list[Tag]:
        return self.session.query(Tag)\
            .filter(Tag.name.ilike(f"{keyword}%"))\
            .limit(10)\
            .all()


    def get_image_path(self, filename: str | Column[str]) -> str:
        filename = str(filename)
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
