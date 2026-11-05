import sys, os
# Set env vars BEFORE any app imports
os.environ["USE_SQLITE"] = "true"
os.environ["DEEPSEEK_API_KEY"] = "test-key"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["SQLITE_PATH"] = "test_system_temp.db"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Now import app modules (env vars are already set)
from app.database import Base, engine, SessionLocal, get_db
from app.main import app
from sqlalchemy import create_engine

# Override to use a simple ASCII path
_tmp_db_path = os.path.join(os.path.dirname(__file__), "_test_system.db")
if os.path.exists(_tmp_db_path):
    os.remove(_tmp_db_path)

new_engine = create_engine(f"sqlite:///{_tmp_db_path}", echo=False, connect_args={"check_same_thread": False})
# Replace the module-level engine
import app.database
app.database.engine = new_engine
# Also update the SessionLocal
app.database.SessionLocal = __import__("sqlalchemy").orm.sessionmaker(autocommit=False, autoflush=False, bind=new_engine)

# Also need to fix the get_db dependency
from app.database import get_db as original_get_db
async def _test_get_db():
    db = app.database.SessionLocal()
    try:
        yield db
    finally:
        db.close()
app.database.get_db = _test_get_db

# Replace in app's dependency_overrides
from app.main import app as fastapi_app
# Override the get_db dependency for all routers
from app.database import get_db as db_dep
fastapi_app.dependency_overrides[db_dep] = _test_get_db


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=new_engine)
    yield
    Base.metadata.drop_all(bind=new_engine)


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        os.remove(_tmp_db_path)
    except:
        pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    resp = client.post("/api/auth/register/password", json={
        "username": "testuser",
        "password": "testpass123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def auth_header(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ==================== 系统测试：知识库上传 ====================

class TestKnowledgeBaseSystem:
    """系统测试：知识库上传与文档管理"""

    def test_tc_kb_01_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_tc_kb_02_upload_txt(self, client, auth_header):
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", b"Hello World\nLine 2", "text/plain")},
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["filename"] == "test.txt"
        assert data["id"] > 0

    def test_tc_kb_03_upload_unsupported(self, client, auth_header):
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("test.exe", b"fake", "application/octet-stream")},
            headers=auth_header,
        )
        assert resp.status_code == 400

    def test_tc_kb_04_list_documents(self, client, auth_header):
        client.post("/api/knowledge/upload",
                     files={"file": ("doc1.txt", b"content1", "text/plain")},
                     headers=auth_header)
        resp = client.get("/api/knowledge/documents", headers=auth_header)
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) >= 1

    def test_tc_kb_05_delete_document(self, client, auth_header):
        up = client.post("/api/knowledge/upload",
                          files={"file": ("delete_me.txt", b"bye", "text/plain")},
                          headers=auth_header).json()
        resp = client.delete(f'/api/knowledge/documents/{up["id"]}', headers=auth_header)
        assert resp.status_code == 200

    def test_tc_kb_06_get_content(self, client, auth_header):
        up = client.post("/api/knowledge/upload",
                          files={"file": ("content.txt", b"Hello content", "text/plain")},
                          headers=auth_header).json()
        resp = client.get(f'/api/knowledge/documents/{up["id"]}/content', headers=auth_header)
        assert resp.status_code == 200
        assert "Hello" in resp.json()["content"]

    def test_tc_kb_07_refresh_index(self, client, auth_header):
        client.post("/api/knowledge/upload",
                     files={"file": ("idx.txt", b"Index me", "text/plain")},
                     headers=auth_header)
        resp = client.post("/api/knowledge/refresh", headers=auth_header)
        assert resp.status_code == 200


# ==================== 系统测试：课程大纲 ====================

class TestOutlineSystem:
    """系统测试：课程大纲"""

    def test_tc_ol_01_generate_empty_kb(self, client, auth_header):
        resp = client.post("/api/course/outline/generate",
                            json={"title": "课程", "file_ids": []},
                            headers=auth_header)
        assert resp.status_code == 400

    def test_tc_ol_02_get_outlines(self, client, auth_header):
        resp = client.get("/api/course/outline", headers=auth_header)
        assert resp.status_code == 200

    def test_tc_ol_03_get_chapters(self, client, auth_header):
        resp = client.get("/api/course/chapters/99999", headers=auth_header)
        assert resp.status_code == 200

    def test_tc_ol_04_delete_nonexist(self, client, auth_header):
        resp = client.delete("/api/course/outline/99999", headers=auth_header)
        assert resp.status_code == 404

    def test_tc_ol_05_get_progress(self, client, auth_header):
        resp = client.get("/api/course/progress", headers=auth_header)
        assert resp.status_code == 200

    def test_tc_ol_06_update_progress(self, client, auth_header):
        resp = client.put("/api/course/progress",
                           json={"chapter_id": 1, "status": "learning"},
                           headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["status"] == "learning"

    def test_tc_ol_07_reset_progress(self, client, auth_header):
        resp = client.post("/api/course/progress/reset", headers=auth_header)
        assert resp.status_code == 200


# ==================== 系统测试：测验答题 ====================

class TestQuizSystem:
    """系统测试：测验"""

    @patch("app.services.vector_store.vector_store.get_all_text", return_value="Mocked")
    def test_tc_qz_01_generate_no_outline(self, mock_get, client, auth_header):
        resp = client.post("/api/quiz/generate-by-course",
                            json={"outline_id": 999, "count": 5, "difficulty": "medium"},
                            headers=auth_header)
        assert resp.status_code == 400

    @patch("app.services.vector_store.vector_store.get_all_text", return_value="Mocked")
    def test_tc_qz_02_generate_no_chapter(self, mock_get, client, auth_header):
        resp = client.post("/api/quiz/generate",
                            json={"chapter_ids": [999], "count": 5},
                            headers=auth_header)
        assert resp.status_code == 400

    def test_tc_qz_03_exam_history(self, client, auth_header):
        resp = client.get("/api/quiz/history", headers=auth_header)
        assert resp.status_code == 200

    def test_tc_qz_04_learning_stats(self, client, auth_header):
        resp = client.get("/api/quiz/progress/stats", headers=auth_header)
        assert resp.status_code == 200

    def test_tc_qz_05_wrong_questions(self, client, auth_header):
        resp = client.get("/api/quiz/wrong-questions", headers=auth_header)
        assert resp.status_code == 200

    def test_tc_qz_06_wrong_stats(self, client, auth_header):
        resp = client.get("/api/quiz/wrong-questions/stats", headers=auth_header)
        assert resp.status_code == 200

    @patch("app.services.vector_store.vector_store.get_all_text", return_value="Mocked")
    def test_tc_qz_07_practice_wrong(self, mock_get, client, auth_header):
        resp = client.post("/api/quiz/wrong-questions/practice", headers=auth_header)
        assert resp.status_code == 200


# ==================== 系统测试：人脸登录 ====================

class TestFaceSystem:
    """系统测试：人脸登录"""

    def test_tc_fl_01_register_face_no_user(self, client):
        import base64
        b64 = base64.b64encode(b"fake_image").decode()
        resp = client.post("/api/auth/register/face",
                            json={"username": "nonexist", "image_base64": b64})
        assert resp.status_code == 404

    def test_tc_fl_02_password_login(self, client):
        client.post("/api/auth/register/password",
                     json={"username": "faceuser", "password": "pass123"})
        resp = client.post("/api/auth/login/password",
                            json={"username": "faceuser", "password": "pass123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_tc_fl_03_password_login_fail(self, client):
        resp = client.post("/api/auth/login/password",
                            json={"username": "nobody", "password": "wrong"})
        assert resp.status_code == 401

    def test_tc_fl_04_face_login_no_image(self, client):
        resp = client.post("/api/auth/login/face",
                            json={"username": "test", "image_base64": ""})
        assert resp.status_code in (400, 422)

    def test_tc_fl_05_delete_exam(self, client, auth_header):
        resp = client.delete("/api/quiz/99999", headers=auth_header)
        assert resp.status_code == 404


# ==================== 系统测试：语音控制 ====================

class TestVoiceSystem:
    """系统测试：语音控制"""

    def test_tc_vc_01_interpret_text(self, client):
        resp = client.post("/api/voice/interpret", json={"text": "回到首页"})
        assert resp.status_code == 200
        assert "command" in resp.json()

    def test_tc_vc_02_interpret_quiz(self, client):
        resp = client.post("/api/voice/interpret", json={"text": "我要做测验"})
        assert resp.status_code == 200

    def test_tc_vc_03_interpret_knowledge(self, client):
        resp = client.post("/api/voice/interpret", json={"text": "打开知识库"})
        assert resp.status_code == 200

    def test_tc_vc_04_interpret_empty(self, client):
        resp = client.post("/api/voice/interpret", json={"text": ""})
        assert resp.status_code == 200
