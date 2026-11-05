import json, time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, distinct
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app.models.quiz import QuizQuestion, ExamResult, WrongQuestion
from app.models.course import Chapter, CourseOutline
from app.schemas.quiz import (
    QuizGenerateByCourseRequest, QuizGenerateRequest,
    QuestionResponse, AnswerSubmit, ExamResultResponse, WrongQuestionResponse
)
from app.services.quiz_engine import QuizEngine
from app.services.vector_store import vector_store
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

def _get_user(user_id):
    return user_id


@router.post("/generate-by-course")
def generate_by_course(
    data: QuizGenerateByCourseRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Generate quiz questions for a full course in ONE LLM call."""
    outline = db.query(CourseOutline).filter(CourseOutline.id == data.outline_id, CourseOutline.user_id == user_id).first()
    if not outline:
        raise HTTPException(status_code=400, detail="未找到该课程")
    chapters = db.query(Chapter).filter(
        Chapter.outline_id == data.outline_id, Chapter.parent_id == 0
    ).order_by(Chapter.sort_order).all()
    if not chapters:
        raise HTTPException(status_code=400, detail="没有找到该课程的章节，请先生成大纲")

    knowledge_text = vector_store.get_all_text()
    if not knowledge_text:
        raise HTTPException(status_code=400, detail="知识库内容为空，请先上传文档")

    chapter_titles = [ch.title for ch in chapters]

    # Distribute total count evenly across chapters, with remainder going to first few
    per_chapter = max(1, data.count // len(chapters))
    remainder = data.count - per_chapter * len(chapters)
    counts_per_chapter = [per_chapter + (1 if i < remainder else 0) for i in range(len(chapters))]

    # Use the max count per chapter for the LLM prompt (it will generate evenly)
    max_per = max(counts_per_chapter)

    start_time = time.time()
    raw_questions = QuizEngine.generate_bulk_quiz(chapter_titles, max_per, data.difficulty)
    if not raw_questions:
        raise HTTPException(status_code=500, detail="题目生成失败，请稍后重试")

    # Distribute questions to match exact user-requested count
    chapter_q_buckets = {i: [] for i in range(len(chapters))}
    for q in raw_questions:
        ch_idx = q.get("chapter_index", 0)
        if 0 <= ch_idx < len(chapters):
            chapter_q_buckets[ch_idx].append(q)

    # Take only the requested number from each chapter
    selected_questions = []
    for i in range(len(chapters)):
        needed = counts_per_chapter[i]
        bucket = chapter_q_buckets.get(i, [])
        selected_questions.extend(bucket[:needed])

    if not selected_questions:
        raise HTTPException(status_code=500, detail="题目生成失败，请稍后重试")

    # Save questions to DB and build response
    all_questions = []
    chapter_map = {idx: ch.id for idx, ch in enumerate(chapters)}

    for q in selected_questions:
        ch_idx = q.get("chapter_index", 0)
        if ch_idx < 0 or ch_idx >= len(chapters):
            ch_idx = 0
        chapter_id = chapter_map.get(ch_idx, chapters[0].id)

        qobj = QuizQuestion(
            chapter_id=chapter_id,
            question_text=q.get("question", ""),
            options_json=q.get("options", {}),
            correct_answer=q.get("answer", ""),
            difficulty=data.difficulty,
            explanation=q.get("explanation", ""),
            exam_id=0,
        )
        db.add(qobj)
        db.flush()
        all_questions.append({
            "id": qobj.id,
            "question": q.get("question"),
            "options": q.get("options"),
            "difficulty": data.difficulty,
            "type": q.get("type", "choice"),
            "chapter_index": ch_idx,
        })

    # Create exam record
    exam = ExamResult(
        user_id=user_id,
        chapter_ids=",".join(str(ch.id) for ch in chapters),
        total=len(all_questions),
        time_limit=data.time_limit,
    )
    db.add(exam)
    db.flush()

    for qid_info in all_questions:
        db.query(QuizQuestion).filter(QuizQuestion.id == qid_info["id"]).update({"exam_id": exam.id})

    db.commit()
    db.refresh(exam)

    elapsed = int(time.time() - start_time)
    return {
        "exam_id": exam.id,
        "questions": all_questions,
        "total": len(all_questions),
        "time_limit": data.time_limit,
        "elapsed": elapsed,
        "message": "题目已生成，请前往考试页面作答",
    }


@router.post("/generate")
def generate_quiz(
    data: QuizGenerateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Generate quiz for specific chapters."""
    chapters = db.query(Chapter).filter(Chapter.id.in_(data.chapter_ids)).order_by(Chapter.sort_order).all()
    if not chapters:
        raise HTTPException(status_code=400, detail="未找到章节，请先生成课程大纲")
    knowledge_text = vector_store.get_all_text()
    if not knowledge_text:
        raise HTTPException(status_code=400, detail="知识库为空，请先上传文档")

    chapter_titles = [ch.title for ch in chapters]

    per_chapter = max(1, data.count // len(chapters))
    remainder = data.count - per_chapter * len(chapters)
    counts_per_chapter = [per_chapter + (1 if i < remainder else 0) for i in range(len(chapters))]
    max_per = max(counts_per_chapter)

    raw_questions = QuizEngine.generate_bulk_quiz(chapter_titles, max_per, data.difficulty)
    if not raw_questions:
        raise HTTPException(status_code=500, detail="题目生成失败，请稍后重试")

    chapter_q_buckets = {i: [] for i in range(len(chapters))}
    for q in raw_questions:
        ch_idx = q.get("chapter_index", 0)
        if 0 <= ch_idx < len(chapters):
            chapter_q_buckets[ch_idx].append(q)

    selected_questions = []
    for i in range(len(chapters)):
        needed = counts_per_chapter[i]
        bucket = chapter_q_buckets.get(i, [])
        selected_questions.extend(bucket[:needed])

    all_questions = []
    chapter_map = {idx: ch.id for idx, ch in enumerate(chapters)}

    for q in selected_questions:
        ch_idx = q.get("chapter_index", 0)
        if ch_idx < 0 or ch_idx >= len(chapters):
            ch_idx = 0
        chapter_id = chapter_map.get(ch_idx, chapters[0].id)
        qobj = QuizQuestion(
            chapter_id=chapter_id,
            question_text=q.get("question", ""),
            options_json=q.get("options", {}),
            correct_answer=q.get("answer", ""),
            difficulty=data.difficulty,
            explanation=q.get("explanation", ""),
            exam_id=0,
        )
        db.add(qobj)
        db.flush()
        all_questions.append({
            "id": qobj.id,
            "question": q.get("question"),
            "options": q.get("options"),
            "difficulty": data.difficulty,
            "type": q.get("type", "choice"),
            "chapter_index": ch_idx,
        })

    exam = ExamResult(
        user_id=user_id,
        chapter_ids=",".join(str(ch.id) for ch in chapters),
        total=len(all_questions),
        time_limit=data.time_limit,
    )
    db.add(exam)
    db.flush()

    for qid_info in all_questions:
        db.query(QuizQuestion).filter(QuizQuestion.id == qid_info["id"]).update({"exam_id": exam.id})

    db.commit()
    db.refresh(exam)

    return {
        "exam_id": exam.id,
        "questions": all_questions,
        "total": len(all_questions),
        "time_limit": data.time_limit,
    }


@router.post("/{exam_id}/submit")
def submit_exam(
    exam_id: int,
    data: AnswerSubmit,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Submit exam answers, auto-grade, and record wrong questions."""
    exam = db.query(ExamResult).filter(ExamResult.id == exam_id, ExamResult.user_id == user_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试记录未找到")
    if exam.score and exam.score > 0:
        raise HTTPException(status_code=400, detail="该考试已提交，不可重复提交")

    question_ids = [int(k) for k in data.answers.keys()]
    questions = db.query(QuizQuestion).filter(QuizQuestion.id.in_(question_ids)).all()
    q_dict = {
        q.id: {
            "_index": i,
            "id": q.id,
            "question": q.question_text,
            "options": q.options_json or {},
            "answer": q.correct_answer,
            "explanation": q.explanation,
            "difficulty": q.difficulty,
        }
        for i, q in enumerate(questions)
    }

    all_qs = []
    exam_qs = db.query(QuizQuestion).filter(QuizQuestion.exam_id == exam_id).all()
    if exam_qs:
        for eq in exam_qs:
            if eq.id in q_dict:
                all_qs.append(q_dict[eq.id])
    else:
        # Fallback: use questions from answers (handles exams before exam_id linking)
        all_qs = list(q_dict.values())

    if not all_qs:
        raise HTTPException(status_code=400, detail="未找到试题数据")

    result = QuizEngine.grade_exam(all_qs, data.answers)

    exam.score = result["score"]
    exam.answers_json = data.answers
    if exam.created_at:
        elapsed = int((datetime.utcnow() - exam.created_at).total_seconds())
        exam.time_spent = max(0, elapsed)
    else:
        exam.time_spent = exam.time_limit or 1800

    existing_wrong = set(
        row[0] for row in db.query(WrongQuestion.question_id).filter(
            WrongQuestion.user_id == user_id,
            WrongQuestion.question_id.in_(result["wrong_ids"]),
        ).all()
    )
    for wrong_id in result["wrong_ids"]:
        if wrong_id not in existing_wrong:
            wq = WrongQuestion(
                user_id=user_id,
                question_id=wrong_id,
                user_answer=data.answers.get(str(wrong_id), ""),
            )
            db.add(wq)

    db.commit()
    return result


@router.get("/{exam_id}/questions")
def get_exam_questions(
    exam_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get questions + exam result for viewing from history."""
    exam = db.query(ExamResult).filter(ExamResult.id == exam_id, ExamResult.user_id == user_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试记录未找到")
    questions = db.query(QuizQuestion).filter(QuizQuestion.exam_id == exam_id).order_by(QuizQuestion.id).all()
    if not questions:
        if exam.chapter_ids:
            cids = [int(x) for x in exam.chapter_ids.split(",") if x.strip().isdigit()]
            if cids:
                questions = db.query(QuizQuestion).filter(QuizQuestion.chapter_id.in_(cids)).order_by(QuizQuestion.id).limit(exam.total).all()

    qlist = [{
        "id": q.id,
        "question": q.question_text,
        "options": q.options_json or {},
        "difficulty": q.difficulty or "medium",
        "type": "choice" if (q.options_json and len(q.options_json) > 2) else "true_false",
    } for q in questions]

    submitted = exam.score is not None and float(exam.score) > 0
    exam_info = {
        "score": exam.score or 0,
        "total": exam.total or len(qlist),
        "time_spent": exam.time_spent or 0,
        "submitted": submitted,
    }

    # If submitted, compute grading result for display
    result = None
    if submitted and exam.answers_json:
        ans = exam.answers_json
        q_dict = {}
        for i, q in enumerate(questions):
            q_dict[q.id] = {
                "_index": i,
                "id": q.id,
                "question": q.question_text,
                "options": q.options_json or {},
                "answer": q.correct_answer,
                "explanation": q.explanation or "",
                "difficulty": q.difficulty or "medium",
            }
        from app.services.quiz_engine import QuizEngine
        qlist_for_grading = list(q_dict.values())
        grade_result = QuizEngine.grade_exam(qlist_for_grading, ans)
        # Add correct_answer to details for display
        exam_info["result"] = grade_result

    return {
        "questions": qlist,
        "exam": exam_info,
    }


@router.get("/history", response_model=List[ExamResultResponse])
def get_exam_history(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get exam history for current user, including course title."""
    exams = (
        db.query(ExamResult)
        .filter(ExamResult.user_id == user_id)
        .order_by(ExamResult.created_at.desc())
        .limit(50)
        .all()
    )

    # Enrich with course title
    result = []
    for exam in exams:
        course_title = None
        if exam.chapter_ids:
            first_cid = exam.chapter_ids.split(",")[0]
            if first_cid:
                try:
                    chapter = db.query(Chapter).filter(Chapter.id == int(first_cid)).first()
                    if chapter:
                        outline = db.query(CourseOutline).filter(CourseOutline.id == chapter.outline_id).first()
                        if outline:
                            course_title = outline.title
                except (ValueError, IndexError):
                    pass

        resp = ExamResultResponse(
            id=exam.id,
            score=exam.score,
            total=exam.total,
            time_spent=exam.time_spent,
            time_limit=exam.time_limit or 1800,
            answers_json=exam.answers_json,
            created_at=exam.created_at,
        )
        resp.course_title = course_title
        # Enrich with chapter titles
        chapter_names = []
        if exam.chapter_ids:
            for cid_str in exam.chapter_ids.split(','):
                if cid_str.strip().isdigit():
                    ch = db.query(Chapter).filter(Chapter.id == int(cid_str)).first()
                    if ch and ch.title:
                        chapter_names.append(ch.title)
        resp.chapter_titles = chapter_names
        result.append(resp)

    return result


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Delete an exam record and its associated wrong questions."""
    exam = db.query(ExamResult).filter(ExamResult.id == exam_id, ExamResult.user_id == user_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试记录未找到")

    # Delete associated quiz questions for this exam
    db.query(QuizQuestion).filter(QuizQuestion.exam_id == exam_id).delete(synchronize_session=False)
    # Delete wrong questions linked to these quiz questions
    exam_q_ids = [q.id for q in db.query(QuizQuestion).filter(QuizQuestion.exam_id == exam_id).all()]
    if exam_q_ids:
        db.query(WrongQuestion).filter(
            WrongQuestion.user_id == user_id,
            WrongQuestion.question_id.in_(exam_q_ids)
        ).delete(synchronize_session=False)
    # Delete exam
    db.delete(exam)
    db.commit()
    return {"message": "考试记录已删除"}


@router.get("/wrong-questions", response_model=List[WrongQuestionResponse])
def get_wrong_questions(
    chapter_id: int = Query(None),
    difficulty: str = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get wrong questions with optional chapter/difficulty filter."""
    wrong_subq = (
        db.query(WrongQuestion.question_id)
        .filter(WrongQuestion.user_id == user_id)
        .distinct()
        .subquery()
    )
    latest_answers = {}
    for w in db.query(WrongQuestion).filter(WrongQuestion.user_id == user_id).all():
        latest_answers[w.question_id] = w.user_answer

    questions = db.query(QuizQuestion).filter(QuizQuestion.id.in_(wrong_subq)).all()
    q_by_id = {q.id: q for q in questions}

    chapter_ids = list(set(q.chapter_id for q in questions))
    chapters = {c.id: c for c in db.query(Chapter).filter(Chapter.id.in_(chapter_ids)).all()} if chapter_ids else {}

    result = []
    seen = set()
    for q_id_str in sorted(latest_answers.keys(), reverse=True):
        q = q_by_id.get(int(q_id_str))
        if not q or q.id in seen:
            continue
        seen.add(q.id)
        if chapter_id and q.chapter_id != chapter_id:
            continue
        if difficulty and q.difficulty != difficulty:
            continue
        ch = chapters.get(q.chapter_id)
        result.append(WrongQuestionResponse(
            id=q.id,
            question_id=q.id,
            question_text=q.question_text,
            correct_answer=q.correct_answer,
            user_answer=latest_answers.get(q.id, ""),
            explanation=q.explanation,
            chapter_title=ch.title if ch else "",
            difficulty=q.difficulty,
            chapter_id=q.chapter_id,
            options=q.options_json or {},
        ))

    return result


@router.post("/wrong-questions/practice")
def practice_wrong_questions(
    chapter_id: int = Query(None),
    difficulty: str = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Generate practice session from wrong questions."""
    wrong_subq = (
        db.query(WrongQuestion.question_id)
        .filter(WrongQuestion.user_id == user_id)
        .distinct()
        .subquery()
    )
    questions = db.query(QuizQuestion).filter(QuizQuestion.id.in_(wrong_subq)).all()

    filtered = []
    for q in questions:
        if chapter_id and q.chapter_id != chapter_id:
            continue
        if difficulty and q.difficulty != difficulty:
            continue
        filtered.append({
            "id": q.id,
            "question": q.question_text,
            "options": q.options_json,
            "difficulty": q.difficulty,
            "type": "choice" if q.options_json and len(q.options_json) > 2 else "true_false",
            "correct_answer": q.correct_answer,
            "explanation": q.explanation or "",
        })

    return {"questions": filtered, "total": len(filtered)}


@router.get("/wrong-questions/stats")
def wrong_question_stats(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get wrong question statistics with trend data."""
    from sqlalchemy import func
    total_count = (
        db.query(func.count(distinct(WrongQuestion.question_id)))
        .filter(WrongQuestion.user_id == user_id)
        .scalar()
    ) or 0

    wrong_qs = db.query(WrongQuestion.question_id).filter(WrongQuestion.user_id == user_id).distinct().all()
    qids = [w[0] for w in wrong_qs]
    questions = db.query(QuizQuestion).filter(QuizQuestion.id.in_(qids)).all() if qids else []

    chapter_counts = {}
    for q in questions:
        chapter_counts[q.chapter_id] = chapter_counts.get(q.chapter_id, 0) + 1

    cids = list(chapter_counts.keys())
    chapters = {}
    if cids:
        for c in db.query(Chapter).filter(Chapter.id.in_(cids)).all():
            chapters[c.id] = c.title

    per_chapter = []
    for cid, cnt in sorted(chapter_counts.items(), key=lambda x: -x[1]):
        per_chapter.append({"chapter_id": cid, "chapter_title": chapters.get(cid, "章节" + str(cid)), "wrong_count": cnt})

    diff_counts = {"easy": 0, "medium": 0, "hard": 0}
    for q in questions:
        d = q.difficulty or "medium"
        diff_counts[d] = diff_counts.get(d, 0) + 1

    exams = db.query(ExamResult).filter(ExamResult.user_id == user_id, ExamResult.score > 0).order_by(ExamResult.created_at.desc()).limit(10).all()
    trend = []
    for e in reversed(exams):
        trend.append({"exam_id": e.id, "score": e.score, "total": e.total, "time_spent": e.time_spent, "created_at": e.created_at.isoformat() if e.created_at else None})

    return {"total_wrong": total_count, "per_chapter": per_chapter, "by_difficulty": diff_counts, "score_trend": trend}


@router.get("/progress/stats")
def get_learning_stats(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get overall learning progress stats."""
    from app.models.course import LearningProgress
    progresses = db.query(LearningProgress).filter(LearningProgress.user_id == user_id).all()
    total = len(progresses)
    completed = sum(1 for p in progresses if p.status == "completed")
    learning = sum(1 for p in progresses if p.status == "learning")
    not_started = sum(1 for p in progresses if p.status == "not_started")
    return {
        "total": total,
        "completed": completed,
        "learning": learning,
        "not_started": not_started,
        "completion_rate": round((completed / total * 100) if total > 0 else 0, 1),
    }
