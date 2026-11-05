import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
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


class ChatMessage(BaseModel):
    role: str
    content: str


class RagChatRequest(BaseModel):
    question: str
    history: List[ChatMessage] = Field(default_factory=list)
    k: int = 5


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


def _prepare(question: str, history: List[ChatMessage], k: int, user_id: int):
    limit = max(1, min(k, 10))
    try:
        sources = vector_store.search(question, limit, user_id=user_id)
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
        for token in LLMService.stream_chat(messages, temperature=0.3):
            if token.startswith("[LLM Error"):
                failed = True
                yield _sse("error", {"message": "大模型调用失败，请检查模型配置或稍后重试。"})
                break
            yield _sse("delta", {"content": token})
        if not failed:
            yield _sse("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
