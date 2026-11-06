import json
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.services.llm_service import LLMService
from app.services.vector_store import vector_store
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/rag", tags=["rag"])

SYSTEM_PROMPT = """你是课程知识库问答助手。请严格依据提供的检索片段回答用户问题。
规则：
1. 只使用片段中的信息作答，不要编造片段之外的内容。
2. 引用信息时在对应句子后标注 [1]、[2] 等编号。
3. 如果片段不足以回答问题，请明确说明“知识库中未找到足够信息”，并指出还需要补充哪些资料。
4. 使用中文回答，条理清晰，必要时分点说明。"""

NO_SOURCE_ANSWER = (
    "知识库中暂未检索到相关内容。请先在「知识库」页面上传课程资料，"
    "并点击「刷新索引」后重试。"
)


class ChatTurn(BaseModel):
    role: str
    content: str


class RagChatRequest(BaseModel):
    question: str
    history: List[ChatTurn] = Field(default_factory=list)
    k: int = 5
    session_id: Optional[int] = None


class RagSource(BaseModel):
    content: str
    score: float
    distance: Optional[float] = None
    filename: Optional[str] = None
    doc_id: Optional[int] = None
    chunk_index: Optional[int] = None


class RagChatResponse(BaseModel):
    answer: str
    sources: List[RagSource]


class EvalCase(BaseModel):
    question: str
    expected_keywords: List[str] = Field(default_factory=list)


class RagEvalRequest(BaseModel):
    cases: List[EvalCase]
    k: int = 5
    modes: List[str] = Field(default_factory=list)


class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    title: str
    message_count: int = 0
    updated_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[Any] = None
    created_at: Optional[datetime] = None


class SessionDetailResponse(BaseModel):
    session: SessionResponse
    messages: List[MessageResponse]


def _build_context(sources: List[dict]) -> str:
    parts = []
    for i, source in enumerate(sources, start=1):
        name = source.get("filename") or "知识库片段"
        parts.append(f"[{i}] 来源：{name}\n{source['content']}")
    return "\n\n".join(parts)


def _filter_sources(sources: List[dict], limit: int) -> List[dict]:
    """Keep the best match and drop clearly weaker / too-distant chunks."""
    if not sources:
        return []
    vector_sources = [s for s in sources if s.get("distance") is not None]
    if not vector_sources:
        return sources[:limit]
    best = min(s["distance"] for s in vector_sources)
    cutoff = best + 0.35
    if settings.rag_max_distance > 0:
        cutoff = min(cutoff, settings.rag_max_distance)
    filtered = [
        s for s in sources
        if s.get("distance") is None or s["distance"] <= cutoff
    ]
    return (filtered or sources[:1])[:limit]


def _prepare(question: str, history: List[ChatTurn], k: int, user_id: int):
    limit = max(1, min(k, 10))
    search_query = question
    if settings.rag_query_rewrite and history:
        try:
            search_query = LLMService.rewrite_query(
                question, [item.model_dump() for item in history]
            ) or question
        except Exception:
            search_query = question
    try:
        sources = vector_store.search(search_query, limit, user_id=user_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"知识库检索不可用：{exc}") from exc
    sources = _filter_sources(sources, limit)
    if not sources:
        return [], None

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-6:]:
        if item.role in ("user", "assistant") and item.content.strip():
            messages.append({"role": item.role, "content": item.content.strip()})
    messages.append({
        "role": "user",
        "content": f"【检索片段】\n{_build_context(sources)}\n\n【用户问题】\n{question}",
    })
    return sources, messages


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _persist_exchange(session_id, user_id, question, answer, sources):
    if not session_id or not answer:
        return
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        ).first()
        if not session:
            return
        db.add(ChatMessage(session_id=session_id, role="user", content=question))
        db.add(ChatMessage(
            session_id=session_id, role="assistant", content=answer, sources=sources
        ))
        if not session.title or session.title == "新对话":
            session.title = question[:40]
        session.updated_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        print("Persist chat failed:", exc)
        db.rollback()
    finally:
        db.close()


@router.post("/chat", response_model=RagChatResponse)
def rag_chat(data: RagChatRequest, user_id: int = Depends(get_current_user)):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    sources, messages = _prepare(question, data.history, data.k, user_id)
    if not sources:
        return RagChatResponse(answer=NO_SOURCE_ANSWER, sources=[])

    answer = LLMService.chat(messages, temperature=0.3)
    if answer.startswith("[LLM Error"):
        raise HTTPException(
            status_code=502,
            detail="大模型调用失败，请检查模型配置或稍后重试。",
        )
    _persist_exchange(data.session_id, user_id, question, answer, sources)
    return RagChatResponse(answer=answer, sources=sources)


@router.post("/chat/stream")
def rag_chat_stream(data: RagChatRequest, user_id: int = Depends(get_current_user)):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    sources, messages = _prepare(question, data.history, data.k, user_id)

    def event_stream():
        yield _sse("sources", {"sources": sources})
        if not sources:
            yield _sse("delta", {"content": NO_SOURCE_ANSWER})
            yield _sse("done", {})
            return
        failed = False
        parts = []
        for token in LLMService.stream_chat(messages, temperature=0.3):
            if token.startswith("[LLM Error"):
                failed = True
                yield _sse("error", {"message": "大模型调用失败，请检查模型配置或稍后重试。"})
                break
            parts.append(token)
            yield _sse("delta", {"content": token})
        if not failed:
            _persist_exchange(data.session_id, user_id, question, "".join(parts), sources)
            yield _sse("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


MODE_LABELS = {
    "bm25": "BM25 关键词",
    "hybrid": "混合检索",
    "vector": "向量检索",
}


def _run_eval(cases, limit, user_id, mode):
    results = []
    hits = 0
    reciprocal_rank = 0.0
    for case in cases:
        sources = vector_store.search(
            case.question, limit, user_id=user_id, mode=mode
        )
        keywords = [kw.strip().lower() for kw in case.expected_keywords if kw.strip()]
        rank = None
        for index, source in enumerate(sources, start=1):
            content = (source.get("content") or "").lower()
            if any(keyword in content for keyword in keywords):
                rank = index
                break
        if rank is not None:
            hits += 1
            reciprocal_rank += 1.0 / rank
        results.append({
            "question": case.question,
            "expected_keywords": case.expected_keywords,
            "hit": rank is not None,
            "rank": rank,
            "top_sources": [
                {
                    "filename": source.get("filename"),
                    "score": source.get("score"),
                    "snippet": (source.get("content") or "")[:160],
                }
                for source in sources[:3]
            ],
        })
    return {
        "summary": {
            "cases": len(cases),
            "hits": hits,
            "hit_rate": round(hits / len(cases), 4),
            "mrr": round(reciprocal_rank / len(cases), 4),
            "k": limit,
        },
        "results": results,
    }


@router.post("/evaluate")
def evaluate_rag(data: RagEvalRequest, user_id: int = Depends(get_current_user)):
    """Evaluate retrieval quality with hit@k / MRR across retrieval modes."""
    cases = [case for case in data.cases if case.expected_keywords][:50]
    if not cases:
        raise HTTPException(status_code=400, detail="请至少提供一条带关键词的评估用例")
    limit = max(1, min(data.k, 10))

    requested = []
    for mode in (data.modes or [settings.retrieval_mode]):
        mode = (mode or "").strip().lower()
        if mode in MODE_LABELS and mode not in requested:
            requested.append(mode)
    if not requested:
        requested = ["bm25"]

    modes = []
    for mode in requested:
        if mode == "vector" and not vector_store.vector_ready():
            modes.append({
                "mode": mode,
                "label": MODE_LABELS[mode],
                "available": False,
                "summary": {
                    "cases": len(cases),
                    "hits": 0,
                    "hit_rate": 0.0,
                    "mrr": 0.0,
                    "k": limit,
                },
                "results": [],
            })
            continue
        try:
            evaluated = _run_eval(cases, limit, user_id, mode)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"检索不可用：{exc}") from exc
        evaluated["mode"] = mode
        evaluated["label"] = MODE_LABELS[mode]
        evaluated["available"] = True
        modes.append(evaluated)

    primary = modes[0]
    return {
        "summary": primary["summary"],
        "results": primary["results"],
        "modes": modes,
    }


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    ids = [session.id for session in sessions]
    counts = {}
    if ids:
        counts = dict(
            db.query(ChatMessage.session_id, func.count(ChatMessage.id))
            .filter(ChatMessage.session_id.in_(ids))
            .group_by(ChatMessage.session_id)
            .all()
        )
    return [
        SessionResponse(
            id=session.id,
            title=session.title or "新对话",
            message_count=counts.get(session.id, 0),
            updated_at=session.updated_at,
        )
        for session in sessions
    ]


@router.post("/sessions", response_model=SessionResponse)
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    session = ChatSession(
        user_id=user_id,
        title=(data.title or "新对话")[:200],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse(
        id=session.id,
        title=session.title or "新对话",
        message_count=0,
        updated_at=session.updated_at,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
        .all()
    )
    return SessionDetailResponse(
        session=SessionResponse(
            id=session.id,
            title=session.title or "新对话",
            message_count=len(messages),
            updated_at=session.updated_at,
        ),
        messages=[
            MessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                sources=message.sources,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "会话已删除"}
