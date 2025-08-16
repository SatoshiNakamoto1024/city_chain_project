# login_app/routes/test_routes.py
import os, sys, copy, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import pytest
from flask import Flask
import login_app.decorators as decorators

# ─── デコレータはテスト中はスキップ ─────────────────────────────
@pytest.fixture(autouse=True)
def stub_require_role(monkeypatch):
    monkeypatch.setattr(decorators, "require_role", lambda role: (lambda f: f))

# ─── account_manager の振る舞いをスタブ ───────────────────────────
@pytest.fixture(autouse=True)
def stub_account_manager(monkeypatch):
    def fake_register_account(data):
        return {"uuid": "fake-uuid", "role": data["role"]}
    def fake_login_account(data):
        return {"success": True, "jwt": "fake-jwt", "role": data["role"]}

    # admin_routes.py 用
    monkeypatch.setattr("login_app.routes.admin_routes.register_account", fake_register_account)
    monkeypatch.setattr("login_app.routes.admin_routes.login_account",    fake_login_account)
    # staff_routes.py 用
    monkeypatch.setattr("login_app.routes.staff_routes.register_account", fake_register_account)
    monkeypatch.setattr("login_app.routes.staff_routes.login_account",    fake_login_account)
    # app_routes.py 用
    monkeypatch.setattr("login_app.routes.app_routes.create_account", fake_register_account)
    monkeypatch.setattr("login_app.routes.app_routes.login",          fake_login_account)

# ─── Flask アプリとテストクライアントのセットアップ ─────────────────
@pytest.fixture
def app():
    app = Flask(__name__)
    from login_app.routes.admin_routes import admin_bp
    from login_app.routes.staff_routes import staff_bp
    from login_app.routes.app_routes   import app_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(app_bp)
    
    # ─── admin_register のデコレータを外して、いつでも通るようにする ─────────────────
    endpoint = "admin_routes.admin_register"
    func = app.view_functions.get(endpoint)
    if hasattr(func, "__wrapped__"):
        app.view_functions[endpoint] = func.__wrapped__

    return app

@pytest.fixture
def client(app):
    return app.test_client()

# ─── 各 role ごとに /register → /login 流れをテスト ─────────────────
@pytest.mark.parametrize("prefix,expected_role", [
    ("/admin", "admin"),
    ("/staff", "staff"),
    ("",       "resident"),
])
def test_register_and_login(prefix, expected_role, client):
    # 登録
    rv = client.post(f"{prefix}/register", json={"username": "u", "password": "p"})
    assert rv.status_code == 200
    result = rv.get_json()
    assert result["role"] == expected_role

    # ログイン
    rv = client.post(f"{prefix}/login", json={"username": "u", "password": "p"})
    assert rv.status_code == 200
    j = rv.get_json()
    assert j["success"] is True
    assert j["role"] == expected_role
