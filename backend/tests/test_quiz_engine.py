import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest


class TestQuizEngine:
    """单元测试：出题算法与评分计算"""

    def test_grade_exam_all_correct(self):
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "explanation": "E1"},
            {"id": 2, "answer": "B", "question": "Q2", "explanation": "E2"},
        ]
        answers = {"1": "A", "2": "B"}
        result = QuizEngine.grade_exam(questions, answers)
        assert result["score"] == 100.0
        assert result["correct"] == 2
        assert result["total"] == 2
        assert len(result["wrong_ids"]) == 0

    def test_grade_exam_all_wrong(self):
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "explanation": "E1"},
            {"id": 2, "answer": "B", "question": "Q2", "explanation": "E2"},
        ]
        answers = {"1": "B", "2": "C"}
        result = QuizEngine.grade_exam(questions, answers)
        assert result["score"] == 0.0
        assert result["correct"] == 0
        assert len(result["wrong_ids"]) == 2

    def test_grade_exam_partial(self):
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "explanation": "E1"},
            {"id": 2, "answer": "B", "question": "Q2", "explanation": "E2"},
            {"id": 3, "answer": "C", "question": "Q3", "explanation": "E3"},
            {"id": 4, "answer": "D", "question": "Q4", "explanation": "E4"},
        ]
        answers = {"1": "A", "2": "B", "3": "X", "4": "Y"}
        result = QuizEngine.grade_exam(questions, answers)
        assert result["score"] == 50.0
        assert result["correct"] == 2
        assert result["total"] == 4
        assert len(result["wrong_ids"]) == 2

    def test_grade_exam_case_insensitive(self):
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "explanation": "E1"},
        ]
        answers = {"1": "a"}
        result = QuizEngine.grade_exam(questions, answers)
        assert result["score"] == 100.0
        assert result["correct"] == 1

    def test_grade_exam_with_whitespace(self):
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "explanation": "E1"},
        ]
        answers = {"1": " A "}
        result = QuizEngine.grade_exam(questions, answers)
        assert result["score"] == 100.0

    def test_empty_questions(self):
        from app.services.quiz_engine import QuizEngine
        result = QuizEngine.grade_exam([], {})
        assert result["score"] == 0
        assert result["total"] == 0
        assert result["correct"] == 0
        assert result["wrong_ids"] == []

    def test_missing_answer_for_question(self):
        from app.services.quiz_engine import QuizEngine
        questions = [{"id": 1, "answer": "A", "question": "Q1", "explanation": "E1"}]
        answers = {}
        result = QuizEngine.grade_exam(questions, answers)
        assert result["score"] == 0.0
        assert result["correct"] == 0
        assert 1 in result["wrong_ids"]

    def test_large_batch_grading(self):
        from app.services.quiz_engine import QuizEngine
        questions = [{"id": i, "answer": "A" if i % 2 == 0 else "B",
                       "question": f"Q{i}", "explanation": "E"} for i in range(100)]
        answers = {str(i): ("A" if i % 2 == 0 else "B") for i in range(100)}
        result = QuizEngine.grade_exam(questions, answers)
        assert result["score"] == 100.0
        assert result["correct"] == 100

    def test_details_structure(self):
        from app.services.quiz_engine import QuizEngine
        questions = [{"id": 1, "answer": "A", "question": "Q1",
                       "options": {"A": "Op1", "B": "Op2"},
                       "explanation": "E1", "difficulty": "easy", "_index": 0}]
        answers = {"1": "A"}
        result = QuizEngine.grade_exam(questions, answers)
        assert len(result["details"]) == 1
        detail = result["details"][0]
        assert detail["question_text"] == "Q1"
        assert detail["user_answer"] == "A"
        assert detail["correct_answer"] == "A"
        assert detail["is_correct"] is True
        assert detail["explanation"] == "E1"
        assert detail["difficulty"] == "easy"

    def test_difficulty_filter_easy(self):
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "difficulty": "easy"},
            {"id": 2, "answer": "B", "question": "Q2", "difficulty": "easy"},
            {"id": 3, "answer": "C", "question": "Q3", "difficulty": "medium"},
        ]
        selected = QuizEngine.select_questions_by_difficulty(questions, "easy", 2)
        assert len(selected) == 2
        assert all(q["difficulty"] == "easy" for q in selected)

    def test_difficulty_filter_not_enough_then_all(self):
        """When not enough matching questions, fallback to all questions."""
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "difficulty": "medium"},
            {"id": 2, "answer": "B", "question": "Q2", "difficulty": "hard"},
        ]
        selected = QuizEngine.select_questions_by_difficulty(questions, "easy", 5)
        assert len(selected) == 2

    def test_difficulty_filter_fallback(self):
        from app.services.quiz_engine import QuizEngine
        questions = [
            {"id": 1, "answer": "A", "question": "Q1", "difficulty": "easy"},
        ]
        selected = QuizEngine.select_questions_by_difficulty(questions, "easy", 5)
        # Only 1 easy, but requested 5 => fallback to all (just 1 question), still returns 1
        assert len(selected) == 1

    def test_generate_bulk_quiz_empty_knowledge(self):
        from app.services.quiz_engine import QuizEngine
        import app.services.vector_store as vs
        original = vs.vector_store.get_all_text
        vs.vector_store.get_all_text = lambda: ""
        try:
            result = QuizEngine.generate_bulk_quiz(["Chapter1"], 3, "medium")
            assert result == []
        finally:
            vs.vector_store.get_all_text = original

    def test_generate_quiz_empty_knowledge(self):
        from app.services.quiz_engine import QuizEngine
        import app.services.vector_store as vs
        original = vs.vector_store.get_all_text
        vs.vector_store.get_all_text = lambda: ""
        try:
            result = QuizEngine.generate_quiz("Chapter1", 3, "medium")
            assert isinstance(result, list)
        finally:
            vs.vector_store.get_all_text = original
