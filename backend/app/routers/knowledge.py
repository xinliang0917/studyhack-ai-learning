import os as _os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from app.config import settings
from app.database import get_db
from app.models.knowledge import KnowledgeDoc, KnowledgeChunk
from app.schemas.knowledge import KnowledgeDocResponse, UploadResponse
from app.services.asr_service import asr_service
from app.services.document_parser import DocumentParser
from app.services.vector_store import vector_store
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

SUPPORTED_TYPES = {"pdf", "docx", "txt", "md", "markdown", "pptx"}
AUDIO_TYPES = {"wav", "mp3", "m4a", "flac", "ogg", "webm"}


def _collect_chunks(db: Session) -> list:
    rows = db.query(KnowledgeChunk, KnowledgeDoc.filename, KnowledgeDoc.user_id).join(
        KnowledgeDoc, KnowledgeChunk.doc_id == KnowledgeDoc.id
    ).all()
    return [
        {
            "content": chunk.content,
            "index": chunk.id,
            "doc_id": chunk.doc_id,
            "chunk_index": chunk.chunk_index,
            "filename": filename,
            "user_id": owner_id,
        }
        for chunk, filename, owner_id in rows
    ]


def _create_document(db, user_id, filename, ext, content, file_path, texts):
    chunks = vector_store.get_chunks_smart(texts)
    doc = KnowledgeDoc(
        user_id=user_id,
        filename=filename,
        file_type=ext,
        file_size=len(content),
        chunk_count=len(chunks),
        file_path=file_path,
    )
    db.add(doc)
    db.flush()
    for i, chunk in enumerate(chunks):
        db.add(KnowledgeChunk(doc_id=doc.id, chunk_index=i, content=chunk["content"]))
    db.commit()
    all_chunks = _collect_chunks(db)
    if all_chunks:
        try:
            vector_store.build_index(all_chunks)
        except Exception as e:
            print(f"Index build after upload: {e}")
    return doc


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"文件超过 {settings.max_upload_mb}MB 限制",
        )
    file_path = DocumentParser.save_upload(content, file.filename, user_id)
    try:
        texts = DocumentParser.parse(file_path, ext)
    except Exception as exc:
        DocumentParser.delete_file(file_path)
        raise HTTPException(status_code=400, detail=f"文档解析失败：{exc}") from exc
    doc = _create_document(
        db, user_id, file.filename, ext, content, file_path, texts
    )
    return UploadResponse(id=doc.id, filename=file.filename, message="Document uploaded and indexed")


@router.post("/transcribe", response_model=UploadResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    if not settings.asr_enabled:
        raise HTTPException(status_code=503, detail="ASR 未启用，请先配置 FunASR")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的音频格式：{ext}")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"文件超过 {settings.max_upload_mb}MB 限制",
        )
    try:
        transcript = asr_service.transcribe(content, file.filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not transcript.strip():
        raise HTTPException(status_code=400, detail="未识别到语音内容")

    text_name = f"{_os.path.splitext(file.filename)[0] or 'audio'}.txt"
    text_bytes = transcript.encode("utf-8")
    file_path = DocumentParser.save_upload(text_bytes, text_name, user_id)
    doc = _create_document(
        db, user_id, text_name, "txt", text_bytes, file_path, [transcript]
    )
    return UploadResponse(
        id=doc.id,
        filename=text_name,
        message=f"音频已转写入库，识别 {len(transcript)} 字",
    )


@router.get("/documents", response_model=List[KnowledgeDocResponse])
def list_documents(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.user_id == user_id).order_by(KnowledgeDoc.upload_time.desc()).all()
    return docs

@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id, KnowledgeDoc.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    deleted_ids = [c.id for c in db.query(KnowledgeChunk).filter(KnowledgeChunk.doc_id == doc_id).all()]
    stored_path = doc.file_path
    db.query(KnowledgeChunk).filter(KnowledgeChunk.doc_id == doc_id).delete()
    db.delete(doc)
    db.commit()
    DocumentParser.delete_file(stored_path)
    if deleted_ids:
        try:
            vector_store.mark_deleted(deleted_ids)
        except Exception as e:
            print(f"Mark deleted failed: {e}")
    if not db.query(KnowledgeChunk).first():
        try:
            vector_store.clear()
        except Exception as e:
            print(f"Index clear after delete: {e}")
    return {"message": "Document deleted"}

@router.post("/refresh")
def refresh_index(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    chunks = _collect_chunks(db)
    if chunks:
        try:
            vector_store.build_index(chunks)
        except Exception as e:
            print(f"Index refresh: {e}")
    else:
        try:
            vector_store.clear()
        except Exception as e:
            print(f"Index clear on refresh: {e}")
    return {"message": "Index refreshed"}

@router.get("/search")
def search_knowledge(
    query: str = Query(...),
    k: int = 5,
    user_id: int = Depends(get_current_user),
):
    return vector_store.search(query, k, user_id=user_id)

@router.get("/documents/{doc_id}/content")
def get_document_content(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id, KnowledgeDoc.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.doc_id == doc_id).order_by(KnowledgeChunk.chunk_index).all()
    content = "\n\n".join(c.content for c in chunks)
    return {"id": doc.id, "filename": doc.filename, "content": content, "file_type": doc.file_type, "file_size": doc.file_size, "chunk_count": len(chunks)}


@router.get("/documents/{doc_id}/chunks/{chunk_index}")
def get_document_chunk(
    doc_id: int,
    chunk_index: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    doc = db.query(KnowledgeDoc).filter(
        KnowledgeDoc.id == doc_id, KnowledgeDoc.user_id == user_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunk = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.doc_id == doc_id,
        KnowledgeChunk.chunk_index == chunk_index,
    ).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {
        "doc_id": doc_id,
        "filename": doc.filename,
        "chunk_index": chunk_index,
        "content": chunk.content,
    }
