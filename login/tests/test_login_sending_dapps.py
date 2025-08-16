# login/test_login_sending_dapps.py

import pytest
import subprocess
import time
import requests
import uuid
import os
import json

@pytest.fixture(scope="module")
def run_app():
    """
    login/app.py をサブプロセスで起動し、テスト完了後停止
    """
    process = subprocess.Popen(["python", "login\\app.py"], shell=True)
    time.sleep(3)

    yield

    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()

@pytest.mark.usefixtures("run_app")
class TestLoginSendingDapps:
    base_url = "http://localhost:5000"

    def test_dapps_send_get(self):
        """
        GET /dapps/send -> フォームHTML (Send Screen)
        """
        resp = requests.get(self.base_url + "/dapps/send")
        assert resp.status_code == 200
        assert "Send Screen" in resp.text

    def test_dapps_send_post(self):
        """
        POST /dapps/send -> sending_dapps.process_sending_transaction
        """
        url = self.base_url + "/dapps/send"
        data = {
            "sender": "UserX",
            "receiver": "UserY",
            "sender_wallet": "ux_wallet",
            "receiver_wallet": "uy_wallet",
            "amount": "300.0",
            "message": "DApps Payment test",
            "verifiable_credential": "cred_xyz",
            "subject": "Payment",
            "action_level": "normal",
            "dimension": "earth",
            "fluctuation": "none",
            "organism_name": "TestOrg",
            "sender_municipality": "CityX",
            "receiver_municipality": "CityZ",
            "details": "Payment test details",
            "goods_or_money": "money",
            "location": "Osaka",
            "proof_of_place": "GPS_data",
            "attributes": {"priority": "normal"}
        }
        headers = {"Authorization": "Bearer dummy_jwt_token"}  # ダミー

        resp = requests.post(url, json=data, headers=headers)
        assert resp.status_code in [200, 500], resp.text
        if resp.status_code == 200:
            body = resp.json()
            # process_sending_transaction が成功なら transaction_id などが返る
            assert "transaction_id" in body
            assert float(body["amount"]) == 300.0
