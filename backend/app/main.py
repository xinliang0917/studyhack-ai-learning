import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db
from app.routers import auth, knowledge, course, quiz, voice, rag, schedule, learning

app = FastAPI(title="AI Learning Assistant", version="1.0.0")

origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_buckets = defaultdict(deque)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not settings.rate_limit_enabled:
        return await call_next(request)
    path = request.url.path
    if not path.startswith("/api/") or path == "/api/health":
        return await call_next(request)

    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    is_auth = path.startswith("/api/auth/")
    limit = (
        settings.auth_rate_limit_per_minute
        if is_auth
        else settings.rate_limit_per_minute
    )
    key = (client_ip, "auth" if is_auth else "api")
    now = time.monotonic()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试"},
            headers={"Retry-After": "60"},
        )
    bucket.append(now)
    return await call_next(request)

# Include routers
app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(course.router)
app.include_router(quiz.router)
app.include_router(voice.router)
app.include_router(rag.router)
app.include_router(schedule.router)
app.include_router(learning.router)

@app.on_event("startup")
def on_startup():
    init_db()
    if settings.seed_demo:
        from app.services.demo_seed import seed_demo
        seed_demo()

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "AI Learning Assistant API is running"}

# Serve frontend static files from repository root/frontend/dist
frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist"
)
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        safe_path = os.path.normpath(full_path).lstrip("\\/")
        if safe_path.startswith("..") or safe_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = os.path.join(frontend_dist, safe_path)
        if safe_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend build not found")
