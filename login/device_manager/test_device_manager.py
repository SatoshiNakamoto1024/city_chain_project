import pytest
import subprocess
import time
import requests
import uuid

@pytest.fixture(scope="module")
def run_device_manager_server():
    # app_device_manager.py を起動
    process = subprocess.Popen(
        ["python", "app_device_manager.py"],
        shell=True
    )
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
        resp = requests.post(f"{self.base_url}/register", json={
            "user_uuid": user_uuid,
            "qr_code": "fakeQRCodeData",
            "device_name": "AdditionalDevice1"
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "device_id" in body

        # テスト間で使えるように保存
        TestDeviceManagerIntegration.user_uuid  = user_uuid
        TestDeviceManagerIntegration.device_id = body["device_id"]

    def test_list_device(self):
        user_uuid = getattr(self, "user_uuid", "")
        resp = requests.get(f"{self.base_url}/list?user_uuid={user_uuid}")
        assert resp.status_code == 200, resp.text
        arr = resp.json()
        assert isinstance(arr, list)

    def test_unbind_device(self):
        user_uuid = TestDeviceManagerIntegration.user_uuid
        device_id = TestDeviceManagerIntegration.device_id
        if not user_uuid or not device_id:
            pytest.skip("前のテストで device_id の取得失敗")
        resp = requests.post(f"{self.base_url}/unbind", json={
            "user_uuid": user_uuid,
            "device_id": device_id
        })
        assert resp.status_code == 200, resp.text

    def test_force_logout(self):
        user_uuid = "test-user-logout-" + uuid.uuid4().hex[:5]
        # dev1 登録
        dev1 = requests.post(f"{self.base_url}/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR1",
            "device_name": "Dev1"
        }).json()
        time.sleep(1)
        # dev2 force=True で登録
        dev2 = requests.post(f"{self.base_url}/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR2",
            "device_name": "Dev2",
            "force": True
        }).json()
        # 古い dev1 が削除され dev2 のみ
        devices = requests.get(f"{self.base_url}/list?user_uuid={user_uuid}").json()
        ids = [d["device_id"] for d in devices]
        assert dev1["device_id"] not in ids
        assert dev2["device_id"] in ids

    def test_reject_and_allow_with_force(self):
        user_uuid = "test-user-force-" + uuid.uuid4().hex[:5]
        # dev1 登録
        resp1 = requests.post(f"{self.base_url}/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR1",
            "device_name": "Primary"
        })
        assert resp1.status_code == 200
        # dev2 force=False で登録拒否
        resp2 = requests.post(f"{self.base_url}/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR2",
            "device_name": "Secondary",
            "force": False
        })
        assert resp2.status_code == 409
        # dev3 force=True で強制ログアウト後登録
        resp3 = requests.post(f"{self.base_url}/register", json={
            "user_uuid": user_uuid,
            "qr_code": "QR3",
            "device_name": "ForcedLogin",
            "force": True
        })
        assert resp3.status_code == 200
        # 最終的に dev3 のみ
        devices = requests.get(f"{self.base_url}/list?user_uuid={user_uuid}").json()
        ids = [d["device_id"] for d in devices]
        assert any(d == resp3.json()["device_id"] for d in ids)
        assert all(d != resp1.json().get("device_id") for d in ids)
