# test_device_manager.py
import pytest
import subprocess
import time
import requests
import uuid
import os

@pytest.fixture(scope="module")
def run_device_manager_server():
    process = subprocess.Popen(["python", "app_device_manager.py"], shell=True)
    time.sleep(3)
    yield
    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()

@pytest.mark.usefixtures("run_device_manager_server")
class TestDeviceManagerIntegration:
    base_url = "http://localhost:5000/device"

    def test_register_device(self):
        user_uuid = "test-user-" + uuid.uuid4().hex[:5]
        resp = requests.post(self.base_url + "/register", json={
            "user_uuid": user_uuid,
            "qr_code": "fakeQRCodeData",
            "device_name": "AdditionalDevice1"
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "device_id" in body, "device_id が含まれていません"

        # 保存して他のテストで使えるように
        self.user_uuid = user_uuid
        self.device_id = body["device_id"]
        TestDeviceManagerIntegration.device_id = body["device_id"]
        TestDeviceManagerIntegration.user_uuid = user_uuid

    def test_list_device(self):
        user_uuid = getattr(self, "user_uuid", "test-user-none")
        resp = requests.get(self.base_url + f"/list?user_uuid={user_uuid}")
        assert resp.status_code == 200, resp.text
        arr = resp.json()
        assert isinstance(arr, list), "レスポンスがリストになっていません"

    def test_unbind_device(self):
        user_uuid = TestDeviceManagerIntegration.user_uuid
        device_id = TestDeviceManagerIntegration.device_id
        if not user_uuid or not device_id:
            pytest.skip("前のテストで device_id の取得に失敗")
        data = {"user_uuid": user_uuid, "device_id": device_id}
        resp = requests.post(self.base_url + "/unbind", json=data)
        assert resp.status_code == 200, resp.text

    def test_force_logout(self):
        user_uuid = "test-user-logout" + uuid.uuid4().hex[:5]

        # dev1: 最初にログイン
        dev1 = requests.post(self.base_url + "/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR1",
            "device_name": "Dev1"
        }).json()
        self.dev1 = dev1

        time.sleep(1)

        # dev2: 後からログイン（force=True で既存を強制ログアウト）
        dev2 = requests.post(self.base_url + "/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR2",
            "device_name": "Dev2",
            "force": True
        }).json()
        self.dev2 = dev2

        # force_logout を明示的に呼ぶ必要はない。登録時に実行されている。
        # 強制ログアウトの効果確認：dev1 は削除されているはず
        devices = requests.get(self.base_url + f"/list?user_uuid={user_uuid}").json()
        device_ids = [d["device_id"] for d in devices]
        assert dev1["device_id"] not in device_ids, "古い端末がログアウトされていません"
        assert dev2["device_id"] in device_ids, "新しい端末が登録されていません"

    def test_reject_and_allow_with_force(self):
        """
        同時利用1台の制限があるときのログイン拒否/強制切断の挙動をテスト
        """
        user_uuid = "test-user-force-" + uuid.uuid4().hex[:5]

        # dev1: 先にログイン（UsersTable 相当）
        resp1 = requests.post(self.base_url + "/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR1",
            "device_name": "Primary"
        })
        assert resp1.status_code == 200
        dev1 = resp1.json()

        # dev2: 強制しない → 拒否されるはず
        resp2 = requests.post(self.base_url + "/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR2",
            "device_name": "Secondary",
            "force": False
        })
        assert resp2.status_code == 409, "force=Falseでも通ってしまっている"

        # dev3: 強制モードでログイン成功
        resp3 = requests.post(self.base_url + "/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR3",
            "device_name": "ForcedLogin",
            "force": True
        })
        assert resp3.status_code == 200, "force=Trueでログインできなかった"
        dev3 = resp3.json()

        # dev1 は削除済みで、dev3 のみが有効
        devices = requests.get(self.base_url + f"/list?user_uuid={user_uuid}").json()
        device_ids = [d["device_id"] for d in devices]
        assert dev1["device_id"] not in device_ids
        assert dev3["device_id"] in device_ids
