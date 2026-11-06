from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Chapter, CourseOutline
from app.models.quiz import ExamResult, QuizQuestion
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/graph/{outline_id}")
def knowledge_graph(
    outline_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    outline = db.query(CourseOutline).filter(
        CourseOutline.id == outline_id,
        CourseOutline.user_id == user_id,
    ).first()
    if not outline:
        raise HTTPException(status_code=404, detail="课程大纲不存在")

    chapters = db.query(Chapter).filter(
        Chapter.outline_id == outline_id
    ).order_by(Chapter.sort_order).all()
    if not chapters:
        raise HTTPException(status_code=400, detail="该大纲还没有章节")

    chapter_ids = {chapter.id for chapter in chapters}
    attempts = defaultdict(int)
    correct = defaultdict(int)

    exams = db.query(ExamResult).filter(ExamResult.user_id == user_id).all()
    for exam in exams:
        if not exam.answers_json:
            continue
        exam_questions = db.query(QuizQuestion).filter(
            QuizQuestion.exam_id == exam.id
        ).all()
        for question in exam_questions:
            if question.chapter_id not in chapter_ids:
                continue
            answer = str(exam.answers_json.get(str(question.id), "")).strip().upper()
            if not answer:
                continue
            attempts[question.chapter_id] += 1
            if answer == (question.correct_answer or "").strip().upper():
                correct[question.chapter_id] += 1

    children = defaultdict(list)
    for chapter in chapters:
        if chapter.parent_id:
            children[chapter.parent_id].append(chapter.id)

    def aggregate(chapter_id):
        total = attempts.get(chapter_id, 0)
        good = correct.get(chapter_id, 0)
        for child_id in children.get(chapter_id, []):
            child_total, child_good = aggregate(child_id)
            total += child_total
            good += child_good
        return total, good

    def mastery(total, good):
        return round(good / total * 100, 1) if total else 0.0

    nodes = []
    for chapter in chapters:
        total, good = aggregate(chapter.id)
        nodes.append({
            "id": chapter.id,
            "title": chapter.title,
            "parent_id": chapter.parent_id,
            "level": 0 if chapter.parent_id == 0 else 1,
            "attempts": total,
            "correct": good,
            "mastery": mastery(total, good),
        })

    root_total = sum(attempts.values())
    root_correct = sum(correct.values())
    root_id = f"outline-{outline.id}"
    nodes.insert(0, {
        "id": root_id,
        "title": outline.title,
        "parent_id": None,
        "level": -1,
        "attempts": root_total,
        "correct": root_correct,
        "mastery": mastery(root_total, root_correct),
    })

    edges = []
    for chapter in chapters:
        parent = chapter.parent_id if chapter.parent_id else root_id
        edges.append({"source": parent, "target": chapter.id})

    top_chapters = [
        node for node in nodes
        if node["parent_id"] == 0
    ]
    return {
        "outline": {"id": outline.id, "title": outline.title},
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "overall_mastery": mastery(root_total, root_correct),
            "attempts": root_total,
            "correct": root_correct,
            "chapter_count": len(chapters),
            "top_chapters": top_chapters,
        },
    }
