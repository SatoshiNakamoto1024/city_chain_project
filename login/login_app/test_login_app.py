# login_app/test_login_app.py
"""
Phase-2 integration test – 本番仕様
 register → (1-step login) → (2-step challenge/verify)
"""

import sys, os, subprocess, time, uuid, base64, json
from pathlib import Path
import pytest, requests, logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Dilithium バインディング
root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir / "ntru" / "dilithium-py"))
from app_dilithium import create_keypair, sign_message      # noqa: E402

SERVER_CMD = ["python", "../login_app/app_login.py"]
BASE_URL   = "http://127.0.0.1:6010"

# logger
logging.basicConfig(level=logging.INFO,
                    format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

MAX_WAIT = 30
CHECK_INTERVAL = 0.5
URL_CHECK_TIMEOUT = 3


# ---------------------------------------------------------------------------
# pytest fixture: サーバー起動 / 終了
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def login_app_server(tmp_path_factory):
    log_file = tmp_path_factory.mktemp("srv") / "server.log"
    with open(log_file, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            SERVER_CMD, stdout=lf, stderr=subprocess.STDOUT, text=True
        )

        start = time.time()
        while time.time() - start < MAX_WAIT:
            if proc.poll() is not None:         # 起動直後に死んだ
                lf.flush()
                print("\n=== server.log ===")
                print(log_file.read_text(encoding="utf-8"))
                pytest.fail("Server process exited prematurely")

            try:
                r = requests.get(f"{BASE_URL}/", timeout=URL_CHECK_TIMEOUT)
                if r.status_code == 200:
                    break                       # 起動確認 OK
            except (requests.ConnectionError, requests.ReadTimeout):
                pass
            time.sleep(CHECK_INTERVAL)
        else:
            lf.flush()
            print("\n=== server.log ===")
            print(log_file.read_text(encoding="utf-8"))
            pytest.fail("Server did not start within 30 s")

        yield
        proc.terminate()
        proc.wait(timeout=5)
        print("\n=== server.log ===")
        print(log_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helper: /register/
# ---------------------------------------------------------------------------
def _register_user() -> dict:
    """ユーザーを1件登録し、テスト用メタを返す"""
    pub, sec = create_keypair()
    username = f"intg_{uuid.uuid4().hex[:6]}"

    payload = {
        "username": username,
        "email":    f"{username}@example.com",
        "password": "TestPass123",
        "public_key": list(pub),
        "secret_key": list(sec)
    }
    res = requests.post(f"{BASE_URL}/register/", json=payload, timeout=30)
    assert res.status_code == 200, f"register failed: {res.text}"
    body = res.json()

    # --- 新フィールドを確認 ---
    assert "wallet_address" in body and body["wallet_address"]
    assert "balance" in body

    return {
        "uuid":            body["uuid"],
        "username":        username,
        "secret_key":      body["secret_key"],
        "fingerprint":     body["fingerprint"],
        "client_cert_b64": body["client_cert"],
        "wallet_address":  body["wallet_address"],
        "balance":         body["balance"],
    }


# ---------------------------------------------------------------------------
# Helper: 1-step login
# ---------------------------------------------------------------------------
def _login_one_step(user: dict) -> str:
    """POST /login/ で JWT を取得し、ウォレット情報も検証"""
    payload = {
        "username":    user["username"],
        "password":    "TestPass123",
        "client_cert": user["client_cert_b64"],
        "device_name": "OneStepDev",
        "force":       True,
    }
    res = requests.post(f"{BASE_URL}/login/", json=payload, timeout=10)
    assert res.status_code == 200, f"/login failed: {res.text}"
    body = res.json()

    # --- 新フィールドを確認 ---
    assert body["wallet_address"] == user["wallet_address"]
    assert isinstance(body["balance"], (int, float))

    return body["jwt_token"]


# ---------------------------------------------------------------------------
# Helper: 2-step login (challenge / verify)
# ---------------------------------------------------------------------------
def _login_two_step(user: dict) -> str:
    """challenge → Dilithium 署名 → verify で JWT を取得"""
    # ① challenge
    chal_body = {
        "uuid":           user["uuid"],
        "password":       "TestPass123",
        "client_cert_fp": user["fingerprint"],
    }
    r = requests.post(f"{BASE_URL}/login/challenge", json=chal_body, timeout=10)
    assert r.status_code == 200, f"challenge failed: {r.text}"
    chal_hex = r.json()["challenge"]

    # ② 署名
    sig_raw = sign_message(bytes.fromhex(chal_hex), bytes(user["secret_key"]))
    sig_b64 = base64.b64encode(bytes(sig_raw)).decode()

    # ③ verify
    ver_body = {"user_uuid": user["uuid"], "signature": sig_b64}
    r2 = requests.post(f"{BASE_URL}/login/verify", json=ver_body, timeout=10)
    assert r2.status_code == 200, f"verify failed: {r2.text}"
    token = r2.json()["jwt_token"]
    assert token.count(".") == 2
    return token


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------
class TestLoginAppProd:

    def test_login_flows(self):
        """register → 1-step → 2-step がすべて成功するか"""
        user = _register_user()

        jwt1 = _login_one_step(user)   # ワンステップ
        jwt2 = _login_two_step(user)   # チャレンジ／署名

        assert jwt1 != jwt2            # 2回とも別トークン

    # Static pages
    @pytest.mark.parametrize("path", ["/", "/login/", "/logout"])
    def test_static_pages(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=5)
        assert r.status_code == 200
