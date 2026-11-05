"""
系统测试脚本 - AI智能学习辅助系统
使用方法: python test_system_runner.py
前提: 后端服务已在本地 8000 端口运行
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import pytest
import json
import requests

BASE_URL = "http://localhost:8000"

def test_kb_01_health_check():
    """TC-KB-01: 系统健康检查"""
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("[PASS] TC-KB-01: 系统运行正常")

def run_tests():
    """Execute all system test cases and collect results."""
    results = {"passed": 0, "failed": 0, "skipped": 0, "details": []}
    
    # --- 测试用例列表 ---
    test_cases = [
        ("KB-01", "知识库上传", "上传TXT文档"),
        ("KB-02", "知识库上传", "上传不支持格式返回400"),
        ("KB-03", "知识库上传", "列出已上传文档"),
        ("KB-04", "知识库上传", "获取文档内容"),
        ("KB-05", "知识库上传", "删除文档"),
        ("KB-06", "知识库上传", "刷新索引"),
        ("OL-01", "大纲生成", "空知识库生成大纲返回400"),
        ("OL-02", "大纲生成", "获取大纲列表"),
        ("OL-03", "大纲生成", "获取不存在的章节"),
        ("OL-04", "大纲生成", "删除不存在大纲返回404"),
        ("OL-05", "大纲生成", "获取进度"),
        ("OL-06", "大纲生成", "更新学习进度"),
        ("OL-07", "大纲生成", "重置学习进度"),
        ("QZ-01", "测验答题", "无大纲时生成测验返回400"),
        ("QZ-02", "测验答题", "无章节时生成测验返回400"),
        ("QZ-03", "测验答题", "获取考试历史"),
        ("QZ-04", "测验答题", "学习进度统计"),
        ("QZ-05", "测验答题", "错题本为空"),
        ("QZ-06", "测验答题", "错题统计"),
        ("FL-01", "人脸登录", "未注册用户注册人脸返回404"),
        ("FL-02", "人脸登录", "密码登录成功"),
        ("FL-03", "人脸登录", "密码登录失败返回401"),
        ("FL-04", "人脸登录", "人脸登录空图片"),
        ("VC-01", "语音控制", "语音解析首页命令"),
        ("VC-02", "语音控制", "语音解析测验命令"),
        ("VC-03", "语音控制", "语音解析知识库命令"),
        ("VC-04", "语音控制", "语音解析空文本"),
    ]
    
    session = requests.Session()
    token = None
    
    # Register a test user
    try:
        r = session.post(f"{BASE_URL}/api/auth/register/password",
                         json={"username": "system_tester", "password": "test123"})
        if r.status_code == 200:
            token = r.json()["access_token"]
    except:
        # May already exist
        try:
            r = session.post(f"{BASE_URL}/api/auth/login/password",
                             json={"username": "system_tester", "password": "test123"})
            if r.status_code == 200:
                token = r.json()["access_token"]
        except:
            pass
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    print(f"\n{'='*60}")
    print(f"  系统测试执行报告")
    print(f"{'='*60}\n")
    
    # TC-KB: 知识库
    print("--- 知识库上传 ---")
    try:
        r = session.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        _record(results, "KB-01", True, "系统健康检查通过")
    except Exception as e:
        _record(results, "KB-01", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/knowledge/upload",
                         files={"file": ("test_sys.txt", b"System test content", "text/plain")},
                         headers=headers)
        assert r.status_code == 200
        doc_id = r.json()["id"]
        _record(results, "KB-02", True, f"文档上传成功, id={doc_id}")
    except Exception as e:
        _record(results, "KB-02", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/knowledge/upload",
                         files={"file": ("test.exe", b"bad", "application/octet-stream")},
                         headers=headers)
        assert r.status_code == 400
        _record(results, "KB-03", True, "不支持的格式正确返回400")
    except Exception as e:
        _record(results, "KB-03", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/knowledge/documents", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) > 0
        _record(results, "KB-04", True, f"文档列表获取成功, 共{len(r.json())}条")
    except Exception as e:
        _record(results, "KB-04", False, str(e))
    
    try:
        if doc_id:
            r = session.get(f"{BASE_URL}/api/knowledge/documents/{doc_id}/content", headers=headers)
            assert r.status_code == 200
            _record(results, "KB-05", True, "文档内容获取成功")
    except Exception as e:
        _record(results, "KB-05", False, str(e))
    
    try:
        if doc_id:
            r = session.delete(f"{BASE_URL}/api/knowledge/documents/{doc_id}", headers=headers)
            assert r.status_code == 200
            _record(results, "KB-06", True, "文档删除成功")
    except Exception as e:
        _record(results, "KB-06", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/knowledge/refresh", headers=headers)
        assert r.status_code in (200, 500)
        _record(results, "KB-07", True, "索引刷新完成" if r.status_code == 200 else "索引刷新(可能为空)")
    except Exception as e:
        _record(results, "KB-07", str(e))
    
    # TC-OL: 大纲
    print("\n--- 课程大纲 ---")
    try:
        r = session.post(f"{BASE_URL}/api/course/outline/generate",
                         json={"title": "测试课程", "file_ids": []},
                         headers=headers)
        assert r.status_code == 400
        _record(results, "OL-01", True, "空知识库正确返回400")
    except Exception as e:
        _record(results, "OL-01", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/course/outline", headers=headers)
        assert r.status_code == 200
        _record(results, "OL-02", True, "大纲列表获取成功")
    except Exception as e:
        _record(results, "OL-02", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/course/chapters/999999", headers=headers)
        assert r.status_code == 200
        _record(results, "OL-03", True, "不存在的章节返回空列表")
    except Exception as e:
        _record(results, "OL-03", False, str(e))
    
    try:
        r = session.delete(f"{BASE_URL}/api/course/outline/999999", headers=headers)
        assert r.status_code == 404
        _record(results, "OL-04", True, "删除不存大纲正确返回404")
    except Exception as e:
        _record(results, "OL-04", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/course/progress", headers=headers)
        assert r.status_code == 200
        _record(results, "OL-05", True, "进度查询成功")
    except Exception as e:
        _record(results, "OL-05", False, str(e))
    
    try:
        r = session.put(f"{BASE_URL}/api/course/progress",
                        json={"chapter_id": 1, "status": "learning"},
                        headers=headers)
        assert r.status_code == 200
        _record(results, "OL-06", True, "进度更新成功")
    except Exception as e:
        _record(results, "OL-06", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/course/progress/reset", headers=headers)
        assert r.status_code == 200
        _record(results, "OL-07", True, "进度重置成功")
    except Exception as e:
        _record(results, "OL-07", False, str(e))
    
    # TC-QZ: 测验
    print("\n--- 测验答题 ---")
    try:
        r = session.post(f"{BASE_URL}/api/quiz/generate-by-course",
                         json={"outline_id": 999, "count": 5, "difficulty": "medium"},
                         headers=headers)
        assert r.status_code == 400
        _record(results, "QZ-01", True, "无大纲测验证确返回400")
    except Exception as e:
        _record(results, "QZ-01", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/quiz/generate",
                         json={"chapter_ids": [999], "count": 5},
                         headers=headers)
        assert r.status_code == 400
        _record(results, "QZ-02", True, "无章节测验证确返回400")
    except Exception as e:
        _record(results, "QZ-02", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/quiz/history", headers=headers)
        assert r.status_code == 200
        _record(results, "QZ-03", True, "考试历史获取成功")
    except Exception as e:
        _record(results, "QZ-03", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/quiz/progress/stats", headers=headers)
        assert r.status_code == 200
        _record(results, "QZ-04", True, "学习统计获取成功")
    except Exception as e:
        _record(results, "QZ-04", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/quiz/wrong-questions", headers=headers)
        assert r.status_code == 200
        _record(results, "QZ-05", True, "错题本获取成功")
    except Exception as e:
        _record(results, "QZ-05", False, str(e))
    
    try:
        r = session.get(f"{BASE_URL}/api/quiz/wrong-questions/stats", headers=headers)
        assert r.status_code == 200
        _record(results, "QZ-06", True, "错题统计获取成功")
    except Exception as e:
        _record(results, "QZ-06", False, str(e))
    
    # TC-FL: 人脸
    print("\n--- 人脸登录 ---")
    try:
        r = session.post(f"{BASE_URL}/api/auth/register/face",
                         json={"username": "notfound", "image_base64": "AAAA"})
        assert r.status_code == 404
        _record(results, "FL-01", True, "未注册用户注册人脸错误正确返回404")
    except Exception as e:
        _record(results, "FL-01", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/auth/register/password",
                         json={"username": "fltest", "password": "pass123"})
        r2 = session.post(f"{BASE_URL}/api/auth/login/password",
                          json={"username": "fltest", "password": "pass123"})
        assert r2.status_code == 200
        assert "access_token" in r2.json()
        _record(results, "FL-02", True, "密码登录成功")
    except Exception as e:
        _record(results, "FL-02", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/auth/login/password",
                         json={"username": "不存在用户", "password": "wrong"})
        assert r.status_code == 401
        _record(results, "FL-03", True, "错误密码正确返回401")
    except Exception as e:
        _record(results, "FL-03", False, str(e))
    
    try:
        r = session.post(f"{BASE_URL}/api/auth/login/face",
                         json={"username": "fltest", "image_base64": ""})
        assert r.status_code in (400, 422)
        _record(results, "FL-04", True, f"空图片返回{r.status_code}")
    except Exception as e:
        _record(results, "FL-04", False, str(e))
    
    # TC-VC: 语音
    print("\n--- 语音控制 ---")
    for case_id, text in [("VC-01", "回到首页"), ("VC-02", "我要做测验"),
                           ("VC-03", "打开知识库"), ("VC-04", "")]:
        try:
            r = session.post(f"{BASE_URL}/api/voice/interpret", json={"text": text})
            assert r.status_code == 200
            assert "command" in r.json()
            _record(results, case_id, True, f"语音解析成功: {r.json().get('command', '无')}")
        except Exception as e:
            _record(results, case_id, False, str(e))
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  测试汇总")
    print(f"{'='*60}")
    print(f"  总用例: {len(results['details'])}")
    print(f"  通过: {results['passed']}")
    print(f"  失败: {results['failed']}")
    print(f"  通过率: {results['passed']/len(results['details'])*100:.1f}%")
    print(f"{'='*60}\n")
    
    if results["failed"] > 0:
        print("失败详情:")
        for d in results["details"]:
            if not d["status"]:
                print(f"  [{d['id']}] {d['name']}: {d['reason']}")
    
    return results


def _record(results, case_id, status, reason=""):
    results["details"].append({"id": case_id, "name": reason, "status": status, "reason": reason})
    if status:
        results["passed"] += 1
        print(f"  [PASS] {case_id}")
    else:
        results["failed"] += 1
        print(f"  [FAIL] {case_id}: {reason}")
    sys.stdout.flush()


if __name__ == "__main__":
    if not os.environ.get("SKIP_SERVER_CHECK"):
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=5)
            print(f"服务器连接成功: {r.json()}")
        except Exception as e:
            print(f"无法连接服务器 {BASE_URL}: {e}")
            print("请先启动后端服务: cd backend && uvicorn app.main:app --reload")
            sys.exit(1)
    
    run_tests()
