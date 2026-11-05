from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    item_type = Column(String(20), default="homework")
    course = Column(String(100), nullable=True)
    due_at = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), default="todo", index=True)
    priority = Column(String(20), default="normal")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
