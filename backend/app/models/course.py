from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, Enum
from app.database import Base
import enum

class ProgressStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    LEARNING = "learning"
    COMPLETED = "completed"

class CourseOutline(Base):
    __tablename__ = "course_outlines"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    outline_json = Column(JSON, nullable=True)
    generated_at = Column(DateTime, server_default=func.now())

class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    outline_id = Column(Integer, nullable=False, index=True)
    parent_id = Column(Integer, default=0, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)

class LearningProgress(Base):
    __tablename__ = "learning_progress"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    chapter_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default=ProgressStatus.NOT_STARTED.value)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
