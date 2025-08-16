# test_lifeform.py

import pytest
import subprocess
import time
import requests
import os
import json
import uuid

@pytest.fixture(scope="module")
def run_lifeform_server():
    """
    lifeform/app_lifeform.py をサブプロセスで起動し、
    テスト完了後に停止する。
    ※ user_manager.user_service.register_lifeform が
       DynamoDBやローカル保存にアクセスするため、
       AWS認証情報やフォルダ書き込み権限が必要。
    """
    process = subprocess.Popen(["python", "lifeform\\app_lifeform.py"], shell=True)
    time.sleep(3)  # サーバー起動待ち

    yield

    # 終了処理
    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()

@pytest.mark.usefixtures("run_lifeform_server")
class TestLifeformIntegration:
    base_url = "http://192.168.3.8:5000/lifeform/"

    def test_get_lifeform_form(self):
        """
        GET /lifeform -> 200 OK & HTML内に '生命体登録' などの文言が含まれるかチェック
        """
        resp = requests.get(self.base_url)
        assert resp.status_code == 200, f"status={resp.status_code}, body={resp.text}"
        assert "生命体" in resp.text  # lifeform.htmlに含まれる想定の文字列

    def test_post_lifeform_json(self):
        """
        POST /lifeform (JSONモード)
        """
        data = {
            "user_id": "test-user-" + uuid.uuid4().hex[:6],
            "team_name": "TestDimTeam",
            "affiliation": "DimAffiliation",
            "municipality": "DimCity",
            "state": "DimState",
            "country": "DimCountry",
            "extra_dimensions": ["ExtraX", "ExtraY"]
        }
        resp = requests.post(self.base_url, json=data)
        assert resp.status_code == 200, f"status={resp.status_code}, body={resp.text}"
        body = resp.json()
        assert "lifeform_id" in body
        assert body["user_id"] == data["user_id"]
        # ローカルに lifeform_data/lifeform-xxx-yyy.json が保存されるはず
        # S3やDynamoDBは user_service側の実装次第

    def test_post_lifeform_form(self):
        """
        POST /lifeform (フォーム)
        form-data: user_id=..., team_name=..., etc.
        """
        form_data = {
            "user_id": "form-user-" + uuid.uuid4().hex[:6],
            "team_name": "FormTeam",
            "affiliation": "FormAffiliation",
            "municipality": "FormCity",
            "state": "FormState",
            "country": "FormCountry",
            "extra_dimensions": json.dumps(["FormX", "FormY"])
        }
        resp = requests.post(self.base_url, data=form_data)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "lifeform_id" in body
        assert body["user_id"] == form_data["user_id"]
