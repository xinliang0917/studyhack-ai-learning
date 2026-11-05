from sqlalchemy import Column, Integer, String, Text, DateTime, func, BigInteger
from app.database import Base

class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(BigInteger, default=0)
    chunk_count = Column(Integer, default=0)
    upload_time = Column(DateTime, server_default=func.now())

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doc_id = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
