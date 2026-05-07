import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


# ─── SQLAlchemy ORM Models ───────────────────────────────────────────────────


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_path = Column(String, nullable=False)
    video_name = Column(String, nullable=False)
    video_size = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    source_lang = Column(String, nullable=True)
    target_lang = Column(String, nullable=False)
    translation_engine = Column(String, nullable=False)
    whisper_model = Column(String, nullable=False)
    progress = Column(Float, default=0.0)
    error_message = Column(String, nullable=True)
    output_file = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    segments = relationship("Segment", back_populates="task", cascade="all, delete-orphan")


class Segment(Base):
    __tablename__ = "segments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    source_text = Column(String, nullable=False)
    translated_text = Column(String, nullable=True)

    task = relationship("Task", back_populates="segments")


# ─── Pydantic Schemas ────────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    video_path: str
    target_lang: str = "zh"
    translation_engine: str = "deepl"
    whisper_model: str = "medium"


class TaskResponse(BaseModel):
    id: str
    video_path: str
    video_name: str
    video_size: int
    status: str
    source_lang: Optional[str] = None
    target_lang: str
    translation_engine: str
    whisper_model: str
    progress: float = 0.0
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SegmentResponse(BaseModel):
    id: str
    task_id: str
    start_time: float
    end_time: float
    source_text: str
    translated_text: Optional[str] = None

    model_config = {"from_attributes": True}


class TaskWithSegments(TaskResponse):
    segments: list[SegmentResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
