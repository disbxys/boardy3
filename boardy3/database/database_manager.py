import hashlib
import os
import shutil
from typing import Optional

import cv2
from sqlalchemy import create_engine, Column, exc
from sqlalchemy.orm import Session

from boardy3.database.exceptions import DatabaseInvalidFile, DatabaseItemDoesNotExist, DatabaseItemExists, ThumbnailCreationException
from boardy3.database.models import Base, Image, image_tag, Tag
from boardy3.utils import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    DEFAULT_PAGE_SIZE = 20

    def __init__(self, is_test=False) -> None:
        db_instance_dirpath = "instance"
        os.makedirs(db_instance_dirpath, exist_ok=True)

        # If in testing context
        self.is_test = is_test

        if self.is_test:
            self.db_filepath = f"{db_instance_dirpath}/test_image_database.db"
            self.engine = create_engine(f"sqlite:///{self.db_filepath}", echo=False)

            self.image_dir_path = os.path.join(
                os.getcwd(), "tests", "db", "image_files"
            )
            self.thumbnail_dir_path = os.path.join(
                os.getcwd(), "tests", "db", "thumbnails"
            )
            os.makedirs(self.image_dir_path, exist_ok=True)
        else:
            self.db_filepath = f"{db_instance_dirpath}/image_database.db"
            self.engine = create_engine(f"sqlite:///{self.db_filepath}", echo=False)

            self.image_dir_path = os.path.join(
                os.getcwd(), "db", "image_files"
            )
            self.thumbnail_dir_path = os.path.join(
                os.getcwd(), "db", "thumbnails"
            )
            os.makedirs(self.image_dir_path, exist_ok=True)

        Base.metadata.create_all(self.engine)

        self.session = Session(self.engine)

    
    def add_image(
            self,
            filepath: str,
            tags: list[str] | None = None,
            is_video: bool = False
    ) -> None:
        if not os.path.exists(filepath):
            raise DatabaseInvalidFile(f"File <{filepath}> does not exists.")

        # Calculate file hash to use as new filename
        image_hash = self.sha256_hash_image_data(filepath)
        
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
        shutil.copy2(filepath, save_path)

        if is_video:
            # Genereate thumbnail
            thumbnail_dir = self.get_thumbnail_dir(new_filename)
            os.makedirs(thumbnail_dir, exist_ok=True)
            thumbnail_path = self.get_thumbnail_path(new_filename)
            create_thumbnail(save_path, thumbnail_path)

        # Create new Image record
        new_image = Image(filename=new_filename, is_video=is_video)

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
    

    def delete_image(self, id: int | Column[int]) -> None:
        image_ = self.get_image(id)
        if image_ is None:
            raise DatabaseItemDoesNotExist(f"Image id: {id} does not exist.")
        
        # Delete image from database
        self.session.delete(image_)
        if not self.is_test: self.save()

        image_path = self.get_image_path(image_.filename)
        # By design, the image file should exist if it had existed in the
        # database unless the image location was tampered with.
        assert os.path.exists(image_path) == True
        # Delete physical file
        os.remove(image_path)
        logger.info(f"Image id deleted from database: {image_.id}")

        if image_.is_video is True:
            thumbnail_path = self.get_thumbnail_path(str(image_.filename))
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                logger.info(f"Thumbnail for image id <{image_.id}> deleted from database")


    def delete_all_images(self) -> None:
        for image_ in self.get_all_images():
            self.delete_image(image_.id)
        self.save()


    def get_image(self, id: int | Column[int]) -> Optional[Image]:
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
    

    def add_video(self, filepath: str, tags: list[str] | None = None) -> None:
        """
        Same as add_image() but also create thumbnail for video (reference
        ChatGPT thread).
        """
        raise NotImplementedError()
    

    def delete_video(self, id: int | Column[int]) -> None:
        """Same as delete_image() but also delete video thumbnail"""
        raise NotImplementedError()
        

    def delete_all_videos(self) -> None:
        """delete_image() but for all videos"""
        raise NotImplementedError()
    

    def get_all_videos(self) -> list[Image]:
        raise NotImplementedError()


    def get_video_count(self) -> int:
        raise NotImplementedError()
    

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
        if not self.is_test: self.save()

        # Attempt to grab newly created tag
        new_tag = self.get_tag_by_name(tag.name)
        if new_tag is None:
            raise DatabaseItemDoesNotExist(f"Tag <{tag.name}> does not exist.")

        logger.info(f"New tag created: <{new_tag.id}> | <{new_tag.name}>.")
    
        return self.get_tag_by_name(name)
    

    def add_tag_to_image(self, tag: Tag, image_id: int | Column[int]) -> bool:
        # Verify image id
        if image:= self.get_image(image_id):
            # Verify the tag exists
            if self.get_tag_by_name(tag.name) is None:
                raise DatabaseItemDoesNotExist(f"Tag <{tag.name}> does not exist.")

            # Add tag to image if not on image already.
            if tag not in image.tags:
                image.tags.append(tag)
                logger.info(f"Added tag <{tag.name}> to image <{image.id}>.")

                if not self.is_test: self.save()
                return True
            else:
                logger.info(f"Tag <{tag.name}> already exists for image <{image_id}>.")
                return False
        
        raise DatabaseItemDoesNotExist(f"Image id <{image_id}> does not exist.")

    
    def remove_tag_from_image(
            self,
            tag_id: int | Column[int],
            image_id: int | Column[int]
    ):
        self.remove_tags_from_image([tag_id], image_id)

    
    def remove_tags_from_image(
            self,
            tag_ids: list[int | Column[int]],
            image_id: int | Column[int]
    ):
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

            if not self.is_test: self.save()


    def delete_tag(self, tag_id: int | Column[int]):
        self.delete_tags([tag_id])
    

    def delete_tags(self, tag_ids: list[int | Column[int]]):
        deleted_tags = []
        for tag_id in tag_ids:
            tag_ = self.session.query(Tag)\
                .filter(Tag.id == tag_id)\
                .first()
            
            if tag_ is None:
                raise DatabaseItemDoesNotExist(f"Tag id <{tag_id}> does not exist.")
            
            self.session.delete(tag_)
            deleted_tags.append(tag_)

        # Call save after processing all tag ids.
        if not self.is_test: self.save()

        logger.info(
            "Tags deleted from database: {}"\
            .format(" ".join([str(t.name) for t in deleted_tags]))
        )


    def delete_all_tags(self) -> None:
        for tag_ in self.search_tags():
            self.delete_tag(tag_.id)
        self.save()


    def save(self):
        self.session.commit()


    def search_tags(self, keyword: str | None = None) -> list[Tag]:
        q =  self.session.query(Tag)
        if isinstance(keyword, str):
            q = q.filter(Tag.name.ilike(f"{keyword}%"))\
        
        return q.limit(10).all()


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
    

    def sha256_hash_image_data(self, filepath: str) -> str:
        with open(filepath, "rb") as infile:
            return hashlib.sha256(infile.read()).hexdigest()

    
    def get_thumbnail_path(self, filename: str | Column[str]) -> str:
        filename = str(filename)
        # Extract hash from filename and use it with jpg
        thumbnail_filename = f"sample_{os.path.splitext(filename)[0]}.jpg"
        return os.path.join(
            self.get_thumbnail_dir(filename),
            thumbnail_filename
        )
    
    
    def get_thumbnail_dir(self, filename: str) -> str:
        return os.path.normpath(os.path.join(
            self.thumbnail_dir_path,
            f"{filename[:2]}/{filename[2:4]}"
        ))


def create_thumbnail(video_path, thumbnail_path):
    cap = cv2.VideoCapture(video_path)

    # Get the video duration in ms
    total_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) * 1000
    
    # Pick a time to extract a frame from the video
    time = total_duration / 4   # 1/4 into the video

    # Set the position of the frame to capture (in ms)
    cap.set(cv2.CAP_PROP_POS_MSEC, time)

    success, frame = cap.read()

    if success:
        cv2.imwrite(thumbnail_path, frame)
    else:
        raise ThumbnailCreationException()

    # Release the video capture
    cap.release()


if __name__ == "__main__":
    db = DatabaseManager()

    # db.add_image(
    #     filepath="sample_image.jpeg",
    #     tags=["black_and_white"]
    # )

    for item in db.get_all_images():
        print(f"{item.id} | {item.filename} " + ";".join(t.name for t in item.tags))
