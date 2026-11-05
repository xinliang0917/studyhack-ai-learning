import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import not_
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.course import CourseOutline, Chapter, LearningProgress
from app.models.knowledge import KnowledgeChunk, KnowledgeDoc
from app.schemas.course import OutlineGenerateRequest, OutlineResponse, ChapterResponse, ProgressUpdate, ProgressResponse
from app.services.llm_service import LLMService
from app.services.vector_store import vector_store
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/course", tags=["course"])

@router.post("/outline/generate", response_model=OutlineResponse)
def generate_outline(
    data: OutlineGenerateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    if data.file_ids:
        chunks = (
            db.query(KnowledgeChunk)
            .join(KnowledgeDoc, KnowledgeChunk.doc_id == KnowledgeDoc.id)
            .filter(
                KnowledgeChunk.doc_id.in_(data.file_ids),
                KnowledgeDoc.user_id == user_id,
            )
            .all()
        )
        knowledge_text = "\n".join(c.content for c in chunks)
    else:
        knowledge_text = vector_store.get_all_text(user_id=user_id)
    if not knowledge_text:
        raise HTTPException(status_code=400, detail="No knowledge base content. Upload documents first.")
    result = LLMService.generate_outline(knowledge_text, data.title)
    outline = CourseOutline(user_id=user_id, title=data.title, outline_json=result)
    db.add(outline)
    db.flush()
    # Create chapter records
    chapters = result.get("chapters", [])
    sort_order = 0
    for ch in chapters:
        sort_order += 1
        chapter = Chapter(outline_id=outline.id, parent_id=0, title=ch.get("title", ""), sort_order=sort_order)
        db.add(chapter)
        db.flush()
        sections = ch.get("sections", [])
        for sec in sections:
            sort_order += 1
            sub = Chapter(outline_id=outline.id, parent_id=chapter.id, title=sec.get("title", ""), sort_order=sort_order)
            db.add(sub)
            db.flush()
            sub_progress = LearningProgress(user_id=user_id, chapter_id=sub.id, status="not_started")
            db.add(sub_progress)
        progress = LearningProgress(user_id=user_id, chapter_id=chapter.id, status="not_started")
        db.add(progress)
    db.commit()
    db.refresh(outline)
    return outline

@router.get("/outline", response_model=List[OutlineResponse])
def get_outlines(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    outlines = db.query(CourseOutline).filter(CourseOutline.user_id == user_id).order_by(CourseOutline.generated_at.desc()).all()
    return outlines

@router.get("/outline/{outline_id}", response_model=OutlineResponse)
def get_outline_detail(
    outline_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    outline = db.query(CourseOutline).filter(CourseOutline.id == outline_id, CourseOutline.user_id == user_id).first()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return outline

@router.delete("/outline/{outline_id}")
def delete_outline(
    outline_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    outline = db.query(CourseOutline).filter(CourseOutline.id == outline_id, CourseOutline.user_id == user_id).first()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    # Delete progress records for chapters in this outline
    chapter_ids = [ch.id for ch in db.query(Chapter).filter(Chapter.outline_id == outline_id).all()]
    if chapter_ids:
        db.query(LearningProgress).filter(LearningProgress.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
    # Delete chapters
    db.query(Chapter).filter(Chapter.outline_id == outline_id).delete(synchronize_session=False)
    # Delete outline
    db.delete(outline)
    db.commit()
    return {"message": "Outline deleted"}


@router.get("/chapters/{outline_id}", response_model=List[ChapterResponse])
def get_chapters(
    outline_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    chapters = db.query(Chapter).filter(Chapter.outline_id == outline_id).order_by(Chapter.sort_order).all()
    return chapters

@router.post("/chapter/{chapter_id}/generate")
def generate_chapter_content(
    chapter_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    knowledge_text = vector_store.get_all_text(user_id=user_id)
    outline_record = db.query(CourseOutline).filter(CourseOutline.id == chapter.outline_id).first()
    outline_str = json.dumps(outline_record.outline_json, ensure_ascii=False) if outline_record else ""
    content = LLMService.generate_chapter_content(knowledge_text, chapter.title, outline_str)
    chapter.content = content
    db.commit()
    return {"message": "Content generated", "content": content, "chapter_id": chapter_id}

@router.get("/chapter/{chapter_id}")
def get_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {"id": chapter.id, "title": chapter.title, "content": chapter.content or "", "parent_id": chapter.parent_id}

@router.put("/progress", response_model=ProgressResponse)
def update_progress(
    data: ProgressUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    progress = db.query(LearningProgress).filter(
        LearningProgress.user_id == user_id,
        LearningProgress.chapter_id == data.chapter_id,
    ).first()
    if not progress:
        progress = LearningProgress(user_id=user_id, chapter_id=data.chapter_id, status=data.status)
        db.add(progress)
    else:
        progress.status = data.status
    db.commit()
    db.refresh(progress)
    chapter = db.query(Chapter).filter(Chapter.id == data.chapter_id).first()
    return ProgressResponse(
        id=progress.id,
        chapter_id=progress.chapter_id,
        status=progress.status,
        chapter_title=chapter.title if chapter else None,
        updated_at=progress.updated_at,
    )

@router.get("/progress", response_model=List[ProgressResponse])
def get_progress(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    progresses = db.query(LearningProgress).filter(LearningProgress.user_id == user_id).all()
    # Auto-create missing progress records for chapters without them (e.g. old outlines)
    existing_ids = {p.chapter_id for p in progresses}
    user_outline_ids = [o.id for o in db.query(CourseOutline.id).filter(CourseOutline.user_id == user_id).all()]
    if user_outline_ids:
        missing = []
        if existing_ids:
                        missing = db.query(Chapter).filter(
                Chapter.outline_id.in_(user_outline_ids),
                not_(Chapter.id.in_(existing_ids))
            ).all()
        else:
            missing = db.query(Chapter).filter(
                Chapter.outline_id.in_(user_outline_ids)
            ).all()
        for ch in missing:
            if ch.id is None:
                continue
            p = LearningProgress(user_id=user_id, chapter_id=ch.id, status="not_started")
            db.add(p)
            progresses.append(p)
        if missing:
            db.commit()
    result = []
    for p in progresses:
        chapter = db.query(Chapter).filter(Chapter.id == p.chapter_id).first()
        course_title = None
        outline_id = None
        if chapter:
            outline = db.query(CourseOutline).filter(CourseOutline.id == chapter.outline_id).first()
            if outline:
                course_title = outline.title
                outline_id = outline.id
        result.append((chapter.sort_order if chapter else 999999, ProgressResponse(
            id=p.id,
            chapter_id=p.chapter_id,
            status=p.status,
            chapter_title=chapter.title if chapter else None,
            course_title=course_title,
            outline_id=outline_id,
            updated_at=p.updated_at,
        )))
    result.sort(key=lambda x: x[0])
    return [r[1] for r in result]

@router.post("/progress/reset")
def reset_progress(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    db.query(LearningProgress).filter(LearningProgress.user_id == user_id).update({"status": "not_started"})
    db.commit()
    return {"message": "All progress reset"}
