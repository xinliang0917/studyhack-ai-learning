from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class KnowledgeDocResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    upload_time: datetime

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    id: int
    filename: str
    message: str
