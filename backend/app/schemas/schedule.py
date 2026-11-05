from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    title: str
    item_type: str = "homework"
    course: Optional[str] = None
    due_at: Optional[datetime] = None
    status: str = "todo"
    priority: str = "normal"
    notes: Optional[str] = None


class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    item_type: Optional[str] = None
    course: Optional[str] = None
    due_at: Optional[datetime] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: int
    title: str
    item_type: str
    course: Optional[str] = None
    due_at: Optional[datetime] = None
    status: str
    priority: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
