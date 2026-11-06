from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.course import Chapter, CourseOutline, LearningProgress
from app.models.quiz import ExamResult, QuizQuestion, WrongQuestion
from app.models.schedule import ScheduleItem
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


def _naive(value):
    if value is not None and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


@router.get("/dashboard")
def learning_dashboard(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Aggregated learning dashboard: mastery, activity, weak points, today's work."""
    now = datetime.now()
    today = date.today()

    progresses = db.query(LearningProgress).filter(
        LearningProgress.user_id == user_id
    ).all()
    total_chapters = len(progresses)
    completed = sum(1 for p in progresses if p.status == "completed")
    learning = sum(1 for p in progresses if p.status == "learning")
    not_started = sum(1 for p in progresses if p.status == "not_started")
    mastery = round(
        ((completed + learning * 0.5) / total_chapters * 100)
        if total_chapters else 0,
        1,
    )

    wrong_records = db.query(WrongQuestion).filter(
        WrongQuestion.user_id == user_id
    ).order_by(WrongQuestion.id).all()
    latest_wrong = {}
    for record in wrong_records:
        latest_wrong[record.question_id] = record
    question_ids = list(latest_wrong.keys())
    questions = {
        question.id: question
        for question in db.query(QuizQuestion).filter(
            QuizQuestion.id.in_(question_ids)
        ).all()
    } if question_ids else {}
    due_records = [
        record for record in latest_wrong.values()
        if record.next_review_at is None
        or _naive(record.next_review_at) <= now
    ]
    due_records.sort(key=lambda item: _naive(item.next_review_at) or datetime.min)

    chapter_ids = {q.chapter_id for q in questions.values()}
    chapters = {
        chapter.id: chapter
        for chapter in db.query(Chapter).filter(
            Chapter.id.in_(chapter_ids)
        ).all()
    } if chapter_ids else {}
    progress_map = {p.chapter_id: p for p in progresses}

    wrong_by_chapter = Counter(
        question.chapter_id for question in questions.values()
    )
    weak_chapters = []
    for chapter_id, wrong_count in wrong_by_chapter.most_common(5):
        progress = progress_map.get(chapter_id)
        status = progress.status if progress else "not_started"
        chapter_mastery = (
            100 if status == "completed" else 50 if status == "learning" else 0
        )
        chapter = chapters.get(chapter_id)
        weak_chapters.append({
            "chapter_id": chapter_id,
            "outline_id": chapter.outline_id if chapter else None,
            "title": chapter.title if chapter else f"章节{chapter_id}",
            "wrong_count": wrong_count,
            "mastery": chapter_mastery,
            "status": status,
        })

    next_review = []
    for record in due_records[:5]:
        question = questions.get(record.question_id)
        if not question:
            continue
        next_review.append({
            "question_id": question.id,
            "question_text": question.question_text,
            "chapter_title": chapters.get(question.chapter_id).title
            if question.chapter_id in chapters else "",
            "next_review_at": record.next_review_at,
            "interval_days": record.interval_days or 0,
        })

    tasks = db.query(ScheduleItem).filter(
        ScheduleItem.user_id == user_id
    ).all()
    day_start = datetime.combine(today, time.min)
    day_end = day_start + timedelta(days=1)
    today_items = [
        task for task in tasks
        if task.due_at is not None
        and day_start <= _naive(task.due_at) < day_end
    ]
    today_items.sort(key=lambda task: _naive(task.due_at) or datetime.max)
    upcoming = sorted(
        [
            task for task in tasks
            if task.status != "done"
            and task.due_at is not None
            and _naive(task.due_at) >= now
        ],
        key=lambda task: _naive(task.due_at) or datetime.max,
    )[:5]

    exams = db.query(ExamResult).filter(
        ExamResult.user_id == user_id,
        ExamResult.score.isnot(None),
    ).order_by(ExamResult.created_at).all()
    score_trend = [
        {
            "exam_id": exam.id,
            "score": exam.score,
            "total": exam.total,
            "created_at": exam.created_at,
        }
        for exam in exams[-10:]
    ]
    study_minutes = round(sum(exam.time_spent or 0 for exam in exams) / 60)

    activity = Counter()
    active_days = set()

    def record_activity(value):
        value = _naive(value)
        if not value:
            return
        day = value.date()
        active_days.add(day)
        if day >= today - timedelta(days=6):
            activity[day] += 1

    for exam in exams:
        record_activity(exam.created_at)
    for record in wrong_records:
        record_activity(record.last_reviewed_at or record.created_at)
    chat_rows = (
        db.query(ChatMessage.created_at)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.user_id == user_id)
        .all()
    )
    for (created_at,) in chat_rows:
        record_activity(created_at)
    for task in tasks:
        if task.status == "done":
            record_activity(task.updated_at)

    activity_series = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        activity_series.append({
            "date": day.isoformat(),
            "label": day.strftime("%m/%d"),
            "count": activity.get(day, 0),
        })

    streak_cursor = today
    if streak_cursor not in active_days:
        streak_cursor -= timedelta(days=1)
    streak_days = 0
    while streak_cursor in active_days:
        streak_days += 1
        streak_cursor -= timedelta(days=1)

    return {
        "total_chapters": total_chapters,
        "completed": completed,
        "learning": learning,
        "not_started": not_started,
        "completion_rate": round(
            (completed / total_chapters * 100) if total_chapters else 0, 1
        ),
        "mastery": mastery,
        "total_wrong": len(latest_wrong),
        "due_review": len(due_records),
        "today_tasks": len(today_items),
        "today_tasks_done": sum(1 for task in today_items if task.status == "done"),
        "streak_days": streak_days,
        "study_minutes": study_minutes,
        "activity": activity_series,
        "weak_chapters": weak_chapters,
        "next_review": next_review,
        "score_trend": score_trend,
        "today_items": [
            {
                "id": task.id,
                "title": task.title,
                "item_type": task.item_type,
                "status": task.status,
                "priority": task.priority,
                "due_at": task.due_at,
            }
            for task in today_items
        ],
        "upcoming": [
            {
                "id": task.id,
                "title": task.title,
                "item_type": task.item_type,
                "status": task.status,
                "priority": task.priority,
                "due_at": task.due_at,
            }
            for task in upcoming
        ],
    }
