"""接口层集成测试（第七轮审查 2.3）：固化今日验证过的接口行为，防路由层回归。

覆盖：JWT 六项 / 幂等 / 越权 / 软删 / 图谱缓存失效。提取执行器在测试中打桩，
LLM/ASR 链路不在本层测（属于端到端评测范畴）。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

import app.api.routes.extractions as extractions_module  # noqa: E402
from app.main import app  # noqa: E402

H = {"Authorization": "Bearer test-token"}


@pytest.fixture(scope="module")
def client():
    """context manager 进入才会触发 lifespan（种子账号创建）。"""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_login_success_and_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"username": "dev", "password": "test-pass-123"})
    assert r.json()["code"] == 0
    assert "access_token" in r.json()["data"] and "refresh_token" in r.json()["data"]

    r = client.post("/api/v1/auth/login", json={"username": "dev", "password": "bad"})
    assert r.json()["code"] == 1002


def test_refresh_flow(client):
    tokens = client.post(
        "/api/v1/auth/login", json={"username": "dev", "password": "test-pass-123"}
    ).json()["data"]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.json()["code"] == 0
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": "forged"}).json()["code"] == 1002


def test_auth_gates(client):
    assert client.get("/api/v1/capsules").json()["code"] == 1002          # 无 token
    assert client.get("/api/v1/capsules", headers=H).json()["code"] == 0  # 有效 token


def test_manual_extraction_idempotent(client, monkeypatch):
    """同一文案两次提交必须返回同一任务（第七轮审查 2.1 的回归保护）。"""
    monkeypatch.setattr(extractions_module, "run_extraction", lambda *a, **k: None)
    body = {"manual_text": "幂等测试文案：VLOOKUP 步骤一二三四五六七八九十"}
    r1 = client.post("/api/v1/extractions", headers=H, json=body).json()["data"]
    r2 = client.post("/api/v1/extractions", headers=H, json=body).json()["data"]
    assert r1["task_id"] == r2["task_id"]
    assert r1["video_id"] == r2["video_id"]


def test_mutually_exclusive_params(client):
    r = client.post(
        "/api/v1/extractions", headers=H,
        json={"share_text": "a", "manual_text": "b"},
    )
    assert r.json()["code"] == 1001


def test_unresolvable_share_text(client):
    r = client.post("/api/v1/extractions", headers=H, json={"share_text": "没有链接的一段话"})
    assert r.json()["code"] == 2001


def test_capsule_edit_and_soft_delete(client, monkeypatch):
    monkeypatch.setattr(extractions_module, "run_extraction", lambda *a, **k: None)
    r = client.post(
        "/api/v1/extractions", headers=H,
        json={"manual_text": "待删胶囊文案：Excel 数据透视表步骤一二三四五六七八"},
    ).json()["data"]
    task_id = r["task_id"]

    # 提取执行已打桩，手工造一颗胶囊再走编辑/删除
    from app.core.database import SessionLocal
    from app.models import Capsule, CapsuleTag, ExtractionTask, Video, task_public_id

    db = SessionLocal()
    task_id_num = int(task_id.rsplit("_", 1)[1])
    task = db.get(ExtractionTask, task_id_num)
    cap = Capsule(
        video_id=task.video_id, user_id=task.user_id,
        theme="原始主题", category="step", variables=[], steps=["s1"], tags=["x"],
        model="t", prompt_version="step-v1", source_text_digest="0" * 64,
    )
    db.add(cap)
    db.flush()
    db.add(CapsuleTag(capsule_id=cap.id, tag="x"))
    db.commit()
    cid = cap.id
    db.close()

    # 编辑
    r = client.patch(f"/api/v1/capsules/{cid}", headers=H, json={"theme": "改后主题", "tags": ["y"]})
    assert r.json()["data"]["theme"] == "改后主题"

    # 删除（软删）→ 列表消失、详情 404
    assert client.delete(f"/api/v1/capsules/{cid}", headers=H).json()["code"] == 0
    assert client.get(f"/api/v1/capsules/{cid}", headers=H).json()["code"] == 1004


def test_forbidden_returns_404_not_403(client):
    """越权探测不泄露资源存在性（API.md §4）。"""
    assert client.get("/api/v1/capsules/999999", headers=H).status_code == 404


def test_graph_shape(client):
    data = client.get("/api/v1/graph", headers=H).json()["data"]
    assert set(data.keys()) == {"nodes", "edges"}
