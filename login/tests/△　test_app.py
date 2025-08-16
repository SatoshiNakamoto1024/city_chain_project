#!/usr/bin/env python
"""
test_app.py

このファイルは、app.py の各エンドポイントを Flask の test_client() を用いてテストするためのコードです。
"""

import unittest
import json
import uuid
from app import app, USERS_DB, LIFEFORMS_DB

class LoginAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        # 事前にDB（インメモリ）をクリアする
        USERS_DB.clear()
        LIFEFORMS_DB.clear()

    def test_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Welcome to CityChain", response.get_data(as_text=True))

    def test_registration_and_municipality_verify(self):
        # テスト用の登録データ
        registration_data = {
            "name": "Test User",
            "birth_date": "2000-01-01",
            "address": "123 Test Street",
            "mynumber": "123456789012",
            "email": f"test{uuid.uuid4().hex[:6]}@example.com",
            "phone": "08012345678",
            "password": "password123",
            "initial_harmony_token": "100"
        }
        # POST /register
        response = self.client.post("/register", data=registration_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # municipality_verify ページがレンダリングされるかを確認
        self.assertIn("本人確認", response.get_data(as_text=True))
        # 次、本人確認を実施
        verify_response = self.client.post("/municipality_verify", data={"approval_code": "APPROVED"}, follow_redirects=True)
        self.assertEqual(verify_response.status_code, 200)
        data = json.loads(verify_response.get_data(as_text=True))
        self.assertIn("uuid", data)
        self.assertIn("jwt_token", data)

    def test_login(self):
        # まずユーザー登録
        registration_data = {
            "name": "Login User",
            "birth_date": "1990-01-01",
            "address": "456 Login Street",
            "mynumber": "123456789012",
            "email": f"login{uuid.uuid4().hex[:6]}@example.com",
            "phone": "08098765432",
            "password": "password123",
            "initial_harmony_token": "100"
        }
        self.client.post("/register", data=registration_data)
        user_uuid = list(USERS_DB.keys())[-1]
        # ログイン
        login_data = {"uuid": user_uuid, "password": "password123"}
        response = self.client.post("/login", data=login_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertIn("jwt_token", data)

    def test_profile_update(self):
        # ユーザー登録
        registration_data = {
            "name": "Profile User",
            "birth_date": "1985-05-05",
            "address": "789 Profile Ave",
            "mynumber": "123456789012",
            "email": f"profile{uuid.uuid4().hex[:6]}@example.com",
            "phone": "08011223344",
            "password": "password123",
            "initial_harmony_token": "100"
        }
        self.client.post("/register", data=registration_data)
        user_uuid = list(USERS_DB.keys())[-1]
        # プロフィール更新
        update_data = {"uuid": user_uuid, "address": "Updated Address"}
        response = self.client.post("/profile", data=update_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data.get("address"), "Updated Address")

    def test_lifeform_registration(self):
        # ユーザー登録
        registration_data = {
            "name": "Lifeform User",
            "birth_date": "1995-09-09",
            "address": "101 Lifeform Blvd",
            "mynumber": "123456789012",
            "email": f"lifeform{uuid.uuid4().hex[:6]}@example.com",
            "phone": "08055667788",
            "password": "password123",
            "initial_harmony_token": "100"
        }
        self.client.post("/register", data=registration_data)
        user_uuid = list(USERS_DB.keys())[-1]
        # 生命体登録
        lifeform_data = {
            "user_id": user_uuid,
            "team_name": "TestTeam",
            "affiliation": "TestAffiliation",
            "municipality": "TestCity",
            "region": "TestRegion",
            "country": "TestCountry",
            "world_economy": "Global",
            "humanity": "Humanity",
            "earth": "Earth",
            "solar_system": "Solar System",
            "extra_dimension": ["ExtraDimension1", "ExtraDimension2"]
        }
        response = self.client.post("/lifeform", data=lifeform_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertIn("lifeform_id", data)
        self.assertIn("dimensions", data)

if __name__ == '__main__':
    unittest.main()
