from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, Float
from app.database import Base

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chapter_id = Column(Integer, nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    options_json = Column(JSON, nullable=True)
    correct_answer = Column(String(10), nullable=False)
    difficulty = Column(String(20), default="medium")
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    exam_id = Column(Integer, nullable=True, index=True, default=None)
    source_chunks = Column(JSON, nullable=True)

class ExamResult(Base):
    __tablename__ = "exam_results"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    chapter_ids = Column(String(255), nullable=True)
    score = Column(Float, default=0)
    total = Column(Integer, default=0)
    time_limit = Column(Integer, default=1800)
    answers_json = Column(JSON, nullable=True)
    time_spent = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    question_id = Column(Integer, nullable=False)
    user_answer = Column(String(10), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    reviewed = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    next_review_at = Column(DateTime, nullable=True, index=True)
    last_reviewed_at = Column(DateTime, nullable=True)
