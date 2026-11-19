from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.database.base import Base


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(default="text")
    content: str | None = None
    source_url: str | None = None

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_type == "text":
            if not self.content or not self.content.strip():
                raise ValueError("Content is required for text notes")

        elif self.source_type == "url":
            if not self.source_url:
                raise ValueError("Source URL is required for URL items")

        else:
            raise ValueError("source_type must be 'text' or 'url'")

        return self

class ItemResponse(BaseModel):
    id: int
    title: str
    source_type: str
    source_url: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ItemDetailResponse(ItemResponse):
    raw_content: str

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)

    source_type = Column(String(20), nullable=False)
    # note or url

    source_type = Column(
    String(20),
    nullable=False
    )  # text or url

    source_url = Column(
        Text,
        nullable=True
    )

    raw_content = Column(
        Text,
        nullable=False
    )

    content_hash = Column(String(64), nullable=True, index=True)

    status = Column(String(20), default="pending", nullable=False)
    # pending, processing, completed, failed

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks = relationship(
        "Chunk",
        back_populates="item",
        cascade="all, delete-orphan",
    )

    jobs = relationship(
        "IngestionJob",
        back_populates="item",
        cascade="all, delete-orphan",
    )