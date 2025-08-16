# test_session_manager.py

import pytest
import subprocess
import time
import os
import requests
import uuid

@pytest.fixture(scope="module")
def run_session_server():
    """
    session_manager の Flaskサーバー (app_session_manager.py) をサブプロセスで起動し、
    テスト実行後に停止する。
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    proc = subprocess.Popen(
        ["python", os.path.join(project_root, "session_manager/app_session_manager.py")],
        shell=True,
        cwd=project_root
    )
    time.sleep(3)
    yield
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

@pytest.mark.usefixtures("run_session_server")
class TestSessionManagerIntegration:
    base_url = "http://127.0.0.1:5001"

    def test_create_session(self):
        url = f"{self.base_url}/session/create"
        data = {
            "user_uuid": str(uuid.uuid4()),
            "ip_address": "192.168.0.10"
        }
        resp = requests.post(url, json=data)
        assert resp.status_code == 200, f"status={resp.status_code}, body={resp.text}"
        assert "session_id" in resp.json()

    def test_record_login(self):
        url = f"{self.base_url}/session/record_login"
        data = {
            "user_uuid": str(uuid.uuid4()),
            "ip_address": "192.168.10.20"
        }
        resp = requests.post(url, json=data)
        assert resp.status_code == 200
        assert resp.json().get("message") == "login record saved"

    def test_retrieve_session(self):
        user_uuid   = str(uuid.uuid4())
        create_resp = requests.post(f"{self.base_url}/session/create", json={"user_uuid": user_uuid})
        session_id  = create_resp.json()["session_id"]

        ret_resp = requests.get(f"{self.base_url}/session/retrieve?user_uuid={user_uuid}")
        assert ret_resp.status_code == 200
        sessions = ret_resp.json()
        assert any(s["session_id"] == session_id for s in sessions)

    def test_extend_session(self):
        user_uuid  = str(uuid.uuid4())
        create_resp = requests.post(f"{self.base_url}/session/create", json={"user_uuid": user_uuid})
        session_id  = create_resp.json()["session_id"]

        resp_extend = requests.post(f"{self.base_url}/session/extend", json={
            "user_uuid": user_uuid,
            "session_id": session_id,
            "additional_minutes": 15
        })
        assert resp_extend.status_code == 200
        assert "new_login_time" in resp_extend.json()

    def test_analyze_sessions(self):
        user_uuid = str(uuid.uuid4())
        # 2セッション作成
        requests.post(f"{self.base_url}/session/create", json={"user_uuid": user_uuid})
        requests.post(f"{self.base_url}/session/create", json={"user_uuid": user_uuid})

        resp_an = requests.get(f"{self.base_url}/session/analyze?user_uuid={user_uuid}")
        assert resp_an.status_code == 200
        assert resp_an.json().get("session_count", 0) >= 2

    def test_purge_sessions(self):
        user_uuid = str(uuid.uuid4())
        # 作成
        requests.post(f"{self.base_url}/session/create", json={"user_uuid": user_uuid})
        requests.post(f"{self.base_url}/session/create", json={"user_uuid": user_uuid})

        resp = requests.post(f"{self.base_url}/session/purge", json={"retention_days": 0})
        assert resp.status_code == 200

        ret_resp = requests.get(f"{self.base_url}/session/retrieve?user_uuid={user_uuid}")
        data = ret_resp.json()
        # 0日以上なら当日の分も削除され、空 or error
        assert not data or "error" in data

def test_jwt_page_served():
    resp = requests.get("http://127.0.0.1:5001/session/jwt")
    assert resp.status_code == 200
    assert "<title>JWT 状態確認</title>" in resp.text
