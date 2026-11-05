import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest


class TestProgress:
    """单元测试：学习进度更新逻辑"""

    def test_progress_status_valid_values(self):
        from app.models.course import ProgressStatus
        assert ProgressStatus.NOT_STARTED.value == "not_started"
        assert ProgressStatus.LEARNING.value == "learning"
        assert ProgressStatus.COMPLETED.value == "completed"

    def test_progress_all_statuses_distinct(self):
        from app.models.course import ProgressStatus
        values = [s.value for s in ProgressStatus]
        assert len(values) == len(set(values))

    def test_progress_status_transition_from_init(self):
        from app.models.course import LearningProgress
        p = LearningProgress(user_id=1, chapter_id=1, status="not_started")
        assert p.status == "not_started"
        p = LearningProgress(user_id=1, chapter_id=1, status="learning")
        assert p.status == "learning"
        p = LearningProgress(user_id=1, chapter_id=1, status="completed")
        assert p.status == "completed"

    def test_learning_progress_default_values(self):
        from app.models.course import LearningProgress
        p = LearningProgress(user_id=1, chapter_id=1)
        assert p.user_id == 1
        assert p.chapter_id == 1

    def test_scoring_edge_cases(self):
        from app.services.quiz_engine import QuizEngine
        result = QuizEngine.grade_exam(
            [{"id": 1, "answer": "A", "question": "Q?"}],
            {"1": "A"}
        )
        assert result["score"] == 100.0

    def test_scoring_single_wrong(self):
        from app.services.quiz_engine import QuizEngine
        result = QuizEngine.grade_exam(
            [{"id": 1, "answer": "A", "question": "Q?"}],
            {"1": "B"}
        )
        assert result["score"] == 0.0

    def test_scoring_rounding(self):
        from app.services.quiz_engine import QuizEngine
        result = QuizEngine.grade_exam(
            [{"id": i, "answer": "A", "question": f"Q{i}"} for i in range(3)],
            {"0": "A", "1": "B", "2": "C"}
        )
        assert result["score"] == 33.3

    def test_wrong_question_model(self):
        from app.models.quiz import WrongQuestion
        wq = WrongQuestion(user_id=1, question_id=10, user_answer="B")
        assert wq.user_id == 1
        assert wq.question_id == 10
        assert wq.user_answer == "B"
        # reviewed has DB default 0; at init it is None
        # This tests the model structure, not DB persistence
        assert wq.reviewed is None or wq.reviewed == 0

    def test_exam_result_model(self):
        from app.models.quiz import ExamResult
        er = ExamResult(user_id=1, score=85.5, total=10)
        assert er.user_id == 1
        assert er.score == 85.5
        assert er.total == 10
        # time_limit has DB default 1800; at init it is None
        assert er.time_limit is None or er.time_limit == 1800
