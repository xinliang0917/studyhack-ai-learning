from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schedule import ScheduleItem
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

ITEM_TYPES = {"course", "homework", "exam", "other"}
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
