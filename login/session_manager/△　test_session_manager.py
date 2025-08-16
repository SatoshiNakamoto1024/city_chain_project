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
    ※ DynamoDBテーブル LoginHistory に書き込みを行うため、
      AWS認証情報 (AWS_ACCESS_KEY_ID, etc.) が有効である必要あり。
    """
    # テスト開始前にサーバーを起動
    process = subprocess.Popen(["python", "session_manager\\app_session_manager.py"], shell=True)
    time.sleep(3)  # サーバー起動を待機

    yield  # テスト実行

    # テスト完了後、サーバープロセス終了
    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()

@pytest.mark.usefixtures("run_session_server")
class TestSessionManagerIntegration:
    """
    Flaskサーバーに対し requests でアクセスし、
    実際にDynamoDBにセッションを書き込む統合テスト。
    """

    base_url = "http://127.0.0.1:5001/session/"

    def test_create_session(self):
        url = f"{self.base_url}/create"
        data = {
            "user_uuid": str(uuid.uuid4()),
            "ip_address": "192.168.0.10"
        }
        resp = requests.post(url, json=data)
        assert resp.status_code == 200, f"status={resp.status_code}, body={resp.text}"
        body = resp.json()
        assert "session_id" in body, "create_sessionの結果に session_id が含まれるはず"

    def test_record_login(self):
        url = f"{self.base_url}/record_login"
        data = {
            "user_uuid": str(uuid.uuid4()),
            "ip_address": "192.168.10.20"
        }
        resp = requests.post(url, json=data)
        assert resp.status_code == 200, f"status={resp.status_code}, body={resp.text}"
        body = resp.json()
        assert body["message"] == "login record saved"

    def test_retrieve_session(self):
        # まずはセッションを作る
        create_url = f"{self.base_url}/create"
        user_uuid = str(uuid.uuid4())
        data = {"user_uuid": user_uuid}
        create_resp = requests.post(create_url, json=data)
        assert create_resp.status_code == 200
        session_id = create_resp.json()["session_id"]

        # 取得
        retrieve_url = f"{self.base_url}/retrieve?user_uuid={user_uuid}"
        ret_resp = requests.get(retrieve_url)
        assert ret_resp.status_code == 200
        sessions = ret_resp.json()
        assert len(sessions) > 0
        # session_id が含まれるか確認
        found = any(s["session_id"] == session_id for s in sessions)
        assert found, f"作成したセッション {session_id} が retrieve結果に含まれるはず"

    def test_extend_session(self):
        user_uuid = str(uuid.uuid4())
        # まず1つセッション作成
        create_url = f"{self.base_url}/create"
        resp = requests.post(create_url, json={"user_uuid": user_uuid})
        session_info = resp.json()
        session_id = session_info["session_id"]

        # extend
        extend_url = f"{self.base_url}/extend"
        data = {
            "user_uuid": user_uuid,
            "session_id": session_id,
            "additional_minutes": 15
        }
        resp_extend = requests.post(extend_url, json=data)
        assert resp_extend.status_code == 200
        extended = resp_extend.json()
        assert "new_login_time" in extended

    def test_analyze_sessions(self):
        # 事前にセッション作成&ログイン記録
        user_uuid = str(uuid.uuid4())
        create_url = f"{self.base_url}/create"
        requests.post(create_url, json={"user_uuid": user_uuid})
        requests.post(create_url, json={"user_uuid": user_uuid})
        # analyze
        analyze_url = f"{self.base_url}/analyze?user_uuid={user_uuid}"
        resp_an = requests.get(analyze_url)
        assert resp_an.status_code == 200
        result = resp_an.json()
        assert "session_count" in result
        # 2つ作ったので2以上
        assert result["session_count"] >= 2

    def test_purge_sessions(self):
        # 作成
        user_uuid = str(uuid.uuid4())
        requests.post(f"{self.base_url}/create", json={"user_uuid": user_uuid})
        requests.post(f"{self.base_url}/create", json={"user_uuid": user_uuid})
        # Purge
        purge_url = f"{self.base_url}/purge"
        resp = requests.post(purge_url, json={"retention_days": 0})
        assert resp.status_code == 200
        # check
        ret_url = f"{self.base_url}/retrieve?user_uuid={user_uuid}"
        ret_resp = requests.get(ret_url).json()
        # 全部消えたか？
        assert len(ret_resp) == 0 or "error" in ret_resp, "retention_days=0なら当日も含めて削除されるはず"

def test_jwt_page_served():
    resp = requests.get("http://127.0.0.1:5001/session/jwt")
    assert resp.status_code == 200
    assert "<title>JWT 状態確認</title>" in resp.text