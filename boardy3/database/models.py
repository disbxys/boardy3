from typing import TypeAlias
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

# Association Table for many-to-many relationship between Image and Tag
image_tag = Table(
    "image_tag",
    Base.metadata,
    Column("image_id", Integer, ForeignKey("image.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.id"), primary_key=True)
)


class Image(Base):
    __tablename__ = "image"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), unique=True, nullable=False)

    # Define the many-to-many relationship with Tag
    tags = relationship("Tag", secondary=image_tag, backref="images")


    def __repr__(self) -> str:
        return f"Image <{self.filename}>"
    

    def remove_tags(self, tags_to_remove: list["Tag"]) -> None:
        for tag in tags_to_remove:
            if tag in self.tags:
                self.tags.remove(tag)


class Tag(Base):
    __tablename__ = "tag"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


    def __repr__(self) -> str:
        return f"Tag <{self.name}>"


DatabaseItem: TypeAlias = Image | Tag