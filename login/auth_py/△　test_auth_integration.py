# test_auth_integration.py

import unittest
import json
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_py.app_auth import app  # app_auth.py で Flask アプリが定義されていると仮定

class AuthIntegrationTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    # ---------- 登録成功 ----------
    def test_register_success(self):
        username = f"reg_{uuid.uuid4().hex[:6]}"
        payload = {
            "username": username,
            "email": f"{username}@example.com",
            "password": "TestPass123"
        }
        r = self.client.post("/register", json=payload)
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertTrue(body["success"])
        self.assertIn("fingerprint", body)

    # ---------- ログイン成功 ----------
    def test_login_success(self):
        """
        実際の fingerprint を使ってログイン成功を検証（本番と同じ流れ）
        """
        username = "integration_user_" + uuid.uuid4().hex[:6]
        password = "TestPass123"

        # 🔹 ① ユーザー登録（client_cert_fp は送らない！）
        register_payload = {
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "name": "Integration User",
            "birth_date": "2000-01-01",
            "address": "1 Test Street",
            "mynumber": "123456789012",
            "phone": "08000000000",
            "initial_harmony_token": "100"
        }
        reg_response = self.client.post("/register", json=register_payload)
        self.assertEqual(reg_response.status_code, 200, msg="登録に失敗しました")

        reg_data = reg_response.get_json()
        fingerprint = reg_data.get("fingerprint")
        self.assertIsNotNone(fingerprint, "fingerprint がレスポンスに含まれていません")

        # 🔹 ② ログイン時に、その fingerprint を使う（本番同様）
        login_payload = {
            "username": username,
            "password": password,
            "client_cert_fp": fingerprint
        }
        login_response = self.client.post("/login", json=login_payload)
        self.assertEqual(login_response.status_code, 200, msg="ログインに失敗しました")
        login_data = login_response.get_json()
        self.assertIn("jwt_token", login_data, msg="JWTトークンが返されませんでした")

    def test_register_missing_fields(self):
        """
        必須項目が不足している場合、エラーが返ることを検証する。
        """
        payload = {
            "username": "incomplete_user"
            # email, password, client_cert_fp が不足
        }
        response = self.client.post('/register', json=payload)
        self.assertNotEqual(response.status_code, 200, msg="必須項目不足なのに 200 が返された")
        data = response.get_json()
        self.assertIn("error", data, msg="エラー内容が返されなかった")

    def test_login_success(self):
        """
        ユーザー登録後、正しい username, password, client_cert_fp でログインした際に
        JWT トークンが返ることを検証する。
        登録APIから実際の fingerprint を抽出してログインに使用する。
        """
        username = "loginuser_integration"
        password = "loginpassword"
        reg_payload = {
            "username": username,
            "email": "loginuser_integration@example.com",
            "password": password,
            "client_cert_fp": "dummy_cert_fp"  # ダミー値（登録時には実際に生成される）
        }
        reg_response = self.client.post('/register', json=reg_payload)
        self.assertEqual(reg_response.status_code, 200, msg="登録エンドポイントが失敗")
        reg_data = reg_response.get_json()
        self.assertTrue(reg_data.get("success"), msg="登録結果が success でなかった")
        actual_cert_fp = reg_data.get("fingerprint")
        self.assertIsNotNone(actual_cert_fp, msg="登録結果に fingerprint が含まれていない")

        login_payload = {
            "username": username,
            "password": password,
            "client_cert_fp": actual_cert_fp
        }
        login_response = self.client.post('/login', json=login_payload)
        self.assertEqual(login_response.status_code, 200, msg="ログインエンドポイントが 200 を返さなかった")
        login_data = login_response.get_json()
        self.assertIn("jwt_token", login_data, msg="JWT トークンが返却されなかった")

    def test_login_wrong_password(self):
        """
        ユーザー登録後、誤ったパスワードでログインしようとした場合に
        HTTP 401 エラーとなることを検証する。
        """
        username = "wrongpass_integration"
        password = "correctpassword"
        reg_payload = {
            "username": username,
            "email": "wrongpass_integration@example.com",
            "password": password,
            "client_cert_fp": "dummy_cert_fp"
        }
        reg_response = self.client.post('/register', json=reg_payload)
        self.assertEqual(reg_response.status_code, 200, msg="登録エンドポイントが失敗")

        login_payload = {
            "username": username,
            "password": "incorrectpassword",
            "client_cert_fp": reg_response.get_json().get("fingerprint")
        }
        login_response = self.client.post('/login', json=login_payload)
        self.assertEqual(login_response.status_code, 401, msg="誤ったパスワードでも 401 にならなかった")
        login_data = login_response.get_json()
        self.assertIn("error", login_data, msg="エラーメッセージが返されなかった")

    def test_login_wrong_cert_fp(self):
        """
        ユーザー登録後、誤ったクライアント証明書フィンガープリントでログインしようとした場合に
        HTTP 401 エラーとなることを検証する。
        """
        username = "wrongcert_integration"
        password = "userpassword"
        reg_payload = {
            "username": username,
            "email": "wrongcert_integration@example.com",
            "password": password,
            "client_cert_fp": "dummy_cert_fp"
        }
        reg_response = self.client.post('/register', json=reg_payload)
        self.assertEqual(reg_response.status_code, 200, msg="登録エンドポイントが失敗")

        login_payload = {
            "username": username,
            "password": password,
            "client_cert_fp": "incorrect_cert_fp"
        }
        login_response = self.client.post('/login', json=login_payload)
        self.assertEqual(login_response.status_code, 401, msg="誤った証明書フィンガープリントでログインしても 401 にならなかった")
        login_data = login_response.get_json()
        self.assertIn("error", login_data, msg="エラーメッセージが返されなかった")

if __name__ == '__main__':
    unittest.main()
