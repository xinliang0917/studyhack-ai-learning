from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime

class QuizGenerateByCourseRequest(BaseModel):
    outline_id: int
    count: int = 5
    difficulty: str = "medium"
    time_limit: int = 1800

class QuizGenerateRequest(BaseModel):
    chapter_ids: list[int]
    count: int = 5
    difficulty: Optional[str] = "medium"
    time_limit: Optional[int] = 1800

class QuestionResponse(BaseModel):
    id: int
    chapter_id: int
    question_text: str
    options_json: Optional[Any]
    difficulty: str

    class Config:
        from_attributes = True

class AnswerSubmit(BaseModel):
    exam_id: int
    answers: dict

class ExamResultResponse(BaseModel):
    id: int
    score: float
    total: int
    time_spent: int
    time_limit: int
    course_title: Optional[str] = None
    answers_json: Optional[Any]
    chapter_titles: Optional[List[str]] = None
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class WrongQuestionResponse(BaseModel):
    id: int
    question_id: int
    question_text: Optional[str] = None
    correct_answer: Optional[str] = None
    user_answer: Optional[str] = None
    explanation: Optional[str] = None
    chapter_title: Optional[str] = None
    difficulty: Optional[str] = None
    chapter_id: Optional[int] = None
    options: Optional[Any] = None

    class Config:
        from_attributes = True

