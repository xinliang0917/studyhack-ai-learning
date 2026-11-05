import random
from typing import List, Dict, Any
from app.services.llm_service import LLMService
from app.services.vector_store import vector_store

class QuizEngine:
    @staticmethod
    def generate_quiz(chapter_title: str, count: int = 5, difficulty: str = "medium", user_id: int = None) -> List[Dict]:
        """Generate questions for a single chapter (legacy)."""
        knowledge_text = (
            vector_store.get_all_text()
            if user_id is None
            else vector_store.get_all_text(user_id=user_id)
        )
        questions = LLMService.generate_quiz(knowledge_text, chapter_title, count, difficulty)
        return questions

    @staticmethod
    def generate_bulk_quiz(chapter_titles: List[str], count_per_chapter: int = 3, difficulty: str = "medium", user_id: int = None) -> List[Dict]:
        """Generate questions for ALL chapters in a single LLM call.
        Returns list of {chapter_index, question, type, options, answer, explanation, difficulty}.
        """
        knowledge_text = (
            vector_store.get_all_text()
            if user_id is None
            else vector_store.get_all_text(user_id=user_id)
        )
        if not knowledge_text:
            return []
        questions = LLMService.generate_bulk_quiz(
            knowledge_text, chapter_titles, count_per_chapter, difficulty
        )
        # Validate and clean
        validated = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            if not q.get("question") or not q.get("answer"):
                continue
            if "chapter_index" not in q:
                continue
            validated.append(q)
        return validated

    @staticmethod
    def grade_exam(questions: List[Dict], answers: Dict[str, str]) -> Dict[str, Any]:
        """Grade exam and return results with details."""
        total = len(questions)
        correct = 0
        details = []
        wrong_ids = []

        for q in questions:
            qid = q.get("id")
            if qid is None:
                continue
            user_ans = answers.get(str(qid), "")
            correct_ans = q.get("answer", "")
            is_correct = user_ans.strip().upper() == correct_ans.strip().upper()
            if is_correct:
                correct += 1
            else:
                wrong_ids.append(qid)
            details.append({
                "question_index": q.get("_index", 0),
                "question_text": q.get("question", ""),
                "options": q.get("options", {}),
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "difficulty": q.get("difficulty", "medium"),
            })

        score = round((correct / total) * 100, 1) if total > 0 else 0
        return {
            "score": score,
            "correct": correct,
            "total": total,
            "details": details,
            "wrong_ids": wrong_ids,
        }

    @staticmethod
    def select_questions_by_difficulty(questions: List[Dict], difficulty: str, count: int) -> List[Dict]:
        filtered = [q for q in questions if q.get("difficulty", "medium") == difficulty]
        if len(filtered) < count:
            filtered = questions
        return random.sample(filtered, min(count, len(filtered)))
