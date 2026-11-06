import math
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Chapter, CourseOutline
from app.models.schedule import ScheduleItem
from app.models.quiz import QuizQuestion, WrongQuestion
from app.schemas.schedule import (
    AutoPlanRequest,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

ITEM_TYPES = {"course", "homework", "exam", "other", "review"}
STATUSES = {"todo", "doing", "done"}
PRIORITIES = {"low", "normal", "high"}


def _naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _validate(item_type: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None):
    if item_type is not None and item_type not in ITEM_TYPES:
        raise HTTPException(status_code=400, detail="无效的任务类型")
    if status is not None and status not in STATUSES:
        raise HTTPException(status_code=400, detail="无效的状态")
    if priority is not None and priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="无效的优先级")


def _sort_items(items):
    return sorted(
        items,
        key=lambda x: (
            x.status == "done",
            x.due_at is None,
            _naive(x.due_at) or datetime.max,
            x.id,
        ),
    )


@router.get("/items", response_model=list[ScheduleResponse])
def list_items(
    status: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    _validate(item_type=item_type, status=status)
    query = db.query(ScheduleItem).filter(ScheduleItem.user_id == user_id)
    if status:
        query = query.filter(ScheduleItem.status == status)
    if item_type:
        query = query.filter(ScheduleItem.item_type == item_type)
    if start:
        query = query.filter(ScheduleItem.due_at >= _naive(start))
    if end:
        query = query.filter(ScheduleItem.due_at <= _naive(end))
    return _sort_items(query.all())


@router.post("/items", response_model=ScheduleResponse)
def create_item(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="任务标题不能为空")
    _validate(data.item_type, data.status, data.priority)
    item = ScheduleItem(
        user_id=user_id,
        title=title,
        item_type=data.item_type,
        course=(data.course or "").strip() or None,
        due_at=_naive(data.due_at),
        status=data.status,
        priority=data.priority,
        notes=(data.notes or "").strip() or None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=ScheduleResponse)
def update_item(
    item_id: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    item = db.query(ScheduleItem).filter(
        ScheduleItem.id == item_id, ScheduleItem.user_id == user_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")

    values = data.model_dump(exclude_unset=True)
    _validate(values.get("item_type"), values.get("status"), values.get("priority"))

    if "title" in values:
        title = (values["title"] or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="任务标题不能为空")
        values["title"] = title
    if "course" in values:
        values["course"] = (values["course"] or "").strip() or None
    if "notes" in values:
        values["notes"] = (values["notes"] or "").strip() or None
    if "due_at" in values:
        values["due_at"] = _naive(values["due_at"])

    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/items/{item_id}/toggle", response_model=ScheduleResponse)
def toggle_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    item = db.query(ScheduleItem).filter(
        ScheduleItem.id == item_id, ScheduleItem.user_id == user_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    item.status = "todo" if item.status == "done" else "done"
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    item = db.query(ScheduleItem).filter(
        ScheduleItem.id == item_id, ScheduleItem.user_id == user_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(item)
    db.commit()
    return {"message": "任务已删除"}


@router.post("/auto-plan")
def auto_plan(
    data: AutoPlanRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    _validate(item_type=data.item_type)
    outline = db.query(CourseOutline).filter(
        CourseOutline.id == data.outline_id,
        CourseOutline.user_id == user_id,
    ).first()
    if not outline:
        raise HTTPException(status_code=404, detail="课程大纲不存在")
    chapters = db.query(Chapter).filter(
        Chapter.outline_id == outline.id,
        Chapter.parent_id == 0,
    ).order_by(Chapter.sort_order).all()
    if not chapters:
        raise HTTPException(status_code=400, detail="该大纲没有章节")

    start = data.start_date or date.today()
    days = max(1, min(data.days, 60))
    per_day = max(1, math.ceil(len(chapters) / days))
    existing_titles = {
        item.title for item in db.query(ScheduleItem).filter(
            ScheduleItem.user_id == user_id,
            ScheduleItem.course == outline.title,
        ).all()
    }

    created = []
    for idx, chapter in enumerate(chapters):
        title = f"学习：{chapter.title}"
        if title in existing_titles:
            continue
        day_offset = min(idx // per_day, days - 1)
        due_at = datetime.combine(start + timedelta(days=day_offset), time(hour=20))
        item = ScheduleItem(
            user_id=user_id,
            title=title,
            item_type=data.item_type,
            course=outline.title,
            due_at=due_at,
            status="todo",
            priority="normal",
            notes="由课程大纲自动生成",
        )
        db.add(item)
        created.append(item)

    db.commit()
    for item in created:
        db.refresh(item)
    return {"created": len(created), "items": created}


@router.get("/stats")
def schedule_stats(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    items = db.query(ScheduleItem).filter(ScheduleItem.user_id == user_id).all()
    now = datetime.now()
    done = sum(1 for i in items if i.status == "done")
    doing = sum(1 for i in items if i.status == "doing")
    todo = sum(1 for i in items if i.status == "todo")
    overdue = sum(
        1 for i in items
        if i.status != "done" and i.due_at is not None and _naive(i.due_at) < now
    )
    week_later = now + timedelta(days=7)
    upcoming = [
        {
            "id": i.id,
            "title": i.title,
            "item_type": i.item_type,
            "course": i.course,
            "due_at": i.due_at,
            "status": i.status,
            "priority": i.priority,
        }
        for i in _sort_items(items)
        if i.status != "done" and i.due_at is not None and now <= _naive(i.due_at) <= week_later
    ]
    return {
        "total": len(items),
        "todo": todo,
        "doing": doing,
        "done": done,
        "overdue": overdue,
        "upcoming": upcoming,
    }


def complete_review_task(db: Session, user_id: int, question_id: int):
    """Close today's review task associated with a wrong question."""
    prefix = f"[wrong_question:{question_id}:"
    tasks = db.query(ScheduleItem).filter(
        ScheduleItem.user_id == user_id,
        ScheduleItem.notes.like(f"%{prefix}%"),
        ScheduleItem.status != "done",
    ).all()
    for task in tasks:
        task.status = "done"


@router.post("/review-plan")
def create_review_plan(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Create idempotent daily tasks for all wrong questions due today."""
    now = datetime.now()
    latest = {}
    for record in db.query(WrongQuestion).filter(
        WrongQuestion.user_id == user_id
    ).order_by(WrongQuestion.id).all():
        latest[record.question_id] = record

    due_records = [
        record for record in latest.values()
        if record.next_review_at is None or _naive(record.next_review_at) <= now
    ]
    if not due_records:
        return {"created": 0, "due": 0, "items": []}

    question_ids = [record.question_id for record in due_records]
    questions = {
        question.id: question
        for question in db.query(QuizQuestion).filter(
            QuizQuestion.id.in_(question_ids)
        ).all()
    }
    chapter_ids = {q.chapter_id for q in questions.values()}
    chapters = {
        chapter.id: chapter.title
        for chapter in db.query(Chapter).filter(
            Chapter.id.in_(chapter_ids)
        ).all()
    } if chapter_ids else {}

    day_key = date.today().isoformat()
    created = []
    for record in due_records:
        question = questions.get(record.question_id)
        if not question:
            continue
        marker = f"[wrong_question:{question.id}:{day_key}]"
        exists = db.query(ScheduleItem).filter(
            ScheduleItem.user_id == user_id,
            ScheduleItem.notes.like(f"%{marker}%"),
        ).first()
        if exists:
            continue
        due_at = datetime.combine(date.today(), time(hour=20))
        if due_at < now:
            due_at = now + timedelta(hours=1)
        title = f"复习错题：{(question.question_text or '')[:26]}"
        item = ScheduleItem(
            user_id=user_id,
            title=title,
            item_type="review",
            course=chapters.get(question.chapter_id) or "错题复习",
            due_at=due_at,
            status="todo",
            priority="high" if (record.repetitions or 0) == 0 else "normal",
            notes=marker,
        )
        db.add(item)
        created.append(item)

    db.commit()
    for item in created:
        db.refresh(item)
    return {
        "created": len(created),
        "due": len(due_records),
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "due_at": item.due_at,
                "priority": item.priority,
            }
            for item in created
        ],
    }
