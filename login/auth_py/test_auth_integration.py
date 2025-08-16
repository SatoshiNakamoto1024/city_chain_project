# login/auth_py/test_auth_integration.py
"""
auth_py ‑ app_auth の統合テスト

フロー
------
1) /register でユーザー登録（fingerprint はサーバが生成）
2) 登録レスポンスに入っている fingerprint を使って /login
3) パスワード／fingerprint 誤り時は 401 を確認
"""
import os
import sys
import uuid
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from auth_py.app_auth import app   # ← Flask アプリ本体


class AuthIntegrationTest(unittest.TestCase):

    # -------------------------------------------------------------------------
    # テストクライアント準備
    # -------------------------------------------------------------------------
    def setUp(self) -> None:
        app.config["TESTING"] = True
        self.client = app.test_client()

    # -------------------------------------------------------------------------
    # 内部ヘルパ：ユーザー登録
    # -------------------------------------------------------------------------
    def _register_user(self, username: str, password: str) -> dict:
        """
        ユーザーを登録してレスポンス JSON を返す
        * fingerprint はクライアントから送らず、サーバ側で生成させる
        """
        payload = {
            "username": username,
            "email":    f"{username}@example.com",
            "password": password,
            # client_cert_fp は送らない   ← 重要！
            "name":      "Integration‑User",
            "birth_date": "2000‑01‑01",
            "address":    "1 Test Street",
            "mynumber":   "123456789012",
            "phone":      "08000000000",
            "initial_harmony_token": "100"
        }
        resp = self.client.post("/register", json=payload)
        self.assertEqual(resp.status_code, 200, "登録に失敗しました")
        data = resp.get_json()
        self.assertTrue(data.get("success"), "success フラグが立っていません")
        self.assertIn("fingerprint", data, "fingerprint が返っていません")
        return data  # uuid / fingerprint などを含む

    # -------------------------------------------------------------------------
    # ① 登録成功
    # -------------------------------------------------------------------------
    def test_register_success(self):
        username = "reg_ok_" + uuid.uuid4().hex[:6]
        password = "Passw0rd!"
        data = self._register_user(username, password)

        # 返却フィールドを確認
        self.assertIn("uuid", data)
        self.assertIn("client_cert", data)
        self.assertIn("message", data)

    # -------------------------------------------------------------------------
    # ② 必須項目欠落 → エラー
    # -------------------------------------------------------------------------
    def test_register_missing_fields(self):
        payload = {"username": "missing_fields_user"}
        resp = self.client.post("/register", json=payload)
        self.assertNotEqual(
            resp.status_code, 200, msg="必須項目不足なのに 200 が返りました"
        )
        self.assertIn("error", resp.get_json())

    # -------------------------------------------------------------------------
    # ③ 正常ログイン
    # -------------------------------------------------------------------------
    def test_login_success(self):
        username = "login_ok_" + uuid.uuid4().hex[:6]
        password = "GoodPw123!"
        reg = self._register_user(username, password)

        login_payload = {
            "username":       username,
            "password":       password,
            "client_cert_fp": reg["fingerprint"],
        }
        resp = self.client.post("/login", json=login_payload)
        self.assertEqual(resp.status_code, 200, "ログインに失敗")
        self.assertIn("jwt_token", resp.get_json(), "JWT が返りませんでした")

    # -------------------------------------------------------------------------
    # ④ パスワード誤り → 401
    # -------------------------------------------------------------------------
    def test_login_wrong_password(self):
        username = "login_badpw_" + uuid.uuid4().hex[:6]
        good_pw  = "GoodPw123!"
        reg = self._register_user(username, good_pw)

        bad_payload = {
            "username":       username,
            "password":       "WrongPw!",
            "client_cert_fp": reg["fingerprint"],
        }
        resp = self.client.post("/login", json=bad_payload)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("error", resp.get_json())

    # -------------------------------------------------------------------------
    # ⑤ fingerprint 誤り → 401
    # -------------------------------------------------------------------------
    def test_login_wrong_cert_fp(self):
        username = "login_badfp_" + uuid.uuid4().hex[:6]
        password = "GoodPw123!"
        _ = self._register_user(username, password)

        bad_payload = {
            "username":       username,
            "password":       password,
            "client_cert_fp": "INCORRECT_FINGERPRINT",
        }
        resp = self.client.post("/login", json=bad_payload)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("error", resp.get_json())


# -------------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
