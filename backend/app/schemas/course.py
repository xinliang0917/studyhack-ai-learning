from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class OutlineGenerateRequest(BaseModel):
    title: str
    file_ids: list[int] = []

class OutlineResponse(BaseModel):
    id: int
    title: str
    outline_json: Optional[Any]
    generated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ChapterResponse(BaseModel):
    id: int
    outline_id: int
    parent_id: int
    title: str
    content: Optional[str]
    sort_order: int

    class Config:
        from_attributes = True

class ProgressUpdate(BaseModel):
    chapter_id: int
    status: str

class ProgressResponse(BaseModel):
    id: int
    chapter_id: int
    status: str
    chapter_title: Optional[str] = None
    course_title: Optional[str] = None
    outline_id: Optional[int] = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
