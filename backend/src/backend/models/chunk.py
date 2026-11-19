
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from backend.database.base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)

    item_id = Column(
        Integer,
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index = Column(Integer, nullable=False)

    content = Column(Text, nullable=False)

    # Nomic Embed Text v1.5
    embedding = Column(Vector(768), nullable=True)

    token_count = Column(Integer, nullable=True)

    item = relationship(
        "Item",
        back_populates="chunks",
    )
