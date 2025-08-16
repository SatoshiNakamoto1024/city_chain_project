# mapping_continental_municipality/test_mapping_municipality.py

import os
import sys
import uuid
import pytest
import boto3
import json

# ───────────────────────────────────────────────────────────────
# テスト用に環境変数を先に設定（モジュールインポート前に行う）
os.environ["AWS_REGION"] = "us-east-1"
os.environ["USER_LOCATION_TABLE"] = "UserLocationMapping"
# ───────────────────────────────────────────────────────────────

# テスト対象モジュールをインポートできるようにパスを調整
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mapping_continental_municipality.config   import USER_LOCATION_TABLE, AWS_REGION
from mapping_continental_municipality.services import set_user_location_mapping, get_users_by_location
from mapping_continental_municipality.app_mapping_municipality import create_mapping_app

# DynamoDB リソース・テーブルを取得する fixture
@pytest.fixture(scope="session")
def dynamodb_resource():
    return boto3.resource("dynamodb", region_name=AWS_REGION)

@pytest.fixture(scope="session")
def user_location_table(dynamodb_resource):
    return dynamodb_resource.Table(USER_LOCATION_TABLE)

# ----------------------------------------
# services.py のテスト
# ----------------------------------------
def test_services_set_and_get(user_location_table):
    """
    1) set_user_location_mapping でレコードを書き込み
    2) get_users_by_location で正しく取得できるかを検証
    """

    # ランダムな UUID を生成してテスト用の地域マッピングを登録
    test_uuid     = "test-" + str(uuid.uuid4())[:8]
    test_cont     = "TestContinent"
    test_country  = "TC"
    test_pref     = "TP"
    test_muni     = "TestMuni"

    # まず念のため同じレコードが過去に残っていないか削除（テストを何度も回せるように）
    test_sk = f"{test_country}#{test_pref}#{test_muni}#{test_uuid}"
    try:
        user_location_table.delete_item(
            Key={"continent": test_cont, "location_uuid": test_sk}
        )
    except Exception:
        pass

    # 1) サービス関数で書き込み
    set_user_location_mapping(test_uuid, test_cont, test_country, test_pref, test_muni)

    # 実際に DynamoDB へ正しく書き込まれたかを get_item で検証
    resp = user_location_table.get_item(
        Key={"continent": test_cont, "location_uuid": test_sk}
    )
    item = resp.get("Item")
    assert item is not None, "DynamoDB にレコードが見つかりません"
    assert item["uuid"] == test_uuid
    assert item["country"] == test_country
    assert item["prefecture"] == test_pref
    assert item["municipality"] == test_muni

    # 2) get_users_by_location で取得できるか
    #    continent だけでクエリしても item が含まれる
    users = get_users_by_location(test_cont)
    found = any(u["uuid"] == test_uuid for u in users)
    assert found, "get_users_by_location(continent) でレコードが見つからない"

    # 3) country も指定して取得できるか
    users = get_users_by_location(test_cont, test_country)
    found = any(u["uuid"] == test_uuid for u in users)
    assert found, "get_users_by_location(continent, country) でレコードが見つからない"

    # 4) prefecture も指定して取得できるか
    users = get_users_by_location(test_cont, test_country, test_pref)
    found = any(u["uuid"] == test_uuid for u in users)
    assert found, "get_users_by_location(continent, country, prefecture) でレコードが見つからない"

    # 5) municipality も指定して取得できるか
    users = get_users_by_location(test_cont, test_country, test_pref, test_muni)
    found = any(u["uuid"] == test_uuid for u in users)
    assert found, "get_users_by_location(continent, country, prefecture, municipality) でレコードが見つからない"


# ----------------------------------------
# routes.py のテスト
# ----------------------------------------
@pytest.fixture
def mapping_app():
    """
    Flask のテスト用アプリを返す fixture
    """
    app = create_mapping_app()
    app.testing = True
    return app

@pytest.fixture
def mapping_client(mapping_app):
    """
    Flask のテストクライアントを返す fixture
    """
    return mapping_app.test_client()


def test_routes_set_and_get(mapping_client, user_location_table):
    """
    1) /mapping/set_mapping (POST) でレコードを書き込み
    2) /mapping/get_users (GET) で取得できるか検証
    """

    test_uuid     = "route-" + str(uuid.uuid4())[:8]
    test_cont     = "RTContinent"
    test_country  = "RTC"
    test_pref     = "RTP"
    test_muni     = "RTMuni"

    # 事前に古いレコードが残っていれば削除
    test_sk = f"{test_country}#{test_pref}#{test_muni}#{test_uuid}"
    try:
        user_location_table.delete_item(
            Key={"continent": test_cont, "location_uuid": test_sk}
        )
    except Exception:
        pass

    # 1) /mapping/set_mapping を呼び出す
    payload = {
        "uuid":         test_uuid,
        "continent":    test_cont,
        "country":      test_country,
        "prefecture":   test_pref,
        "municipality": test_muni
    }
    resp = mapping_client.post("/mapping/set_mapping",
                                data=json.dumps(payload),
                                content_type="application/json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True

    # DynamoDB に本当に書き込まれたか確認
    resp_db = user_location_table.get_item(
        Key={"continent": test_cont, "location_uuid": test_sk}
    )
    assert "Item" in resp_db

    # 2) /mapping/get_users を呼び出して取得できるか
    #    (continent, country, prefecture, municipality すべて指定)
    url = f"/mapping/get_users?continent={test_cont}&country={test_country}&prefecture={test_pref}&municipality={test_muni}"
    resp2 = mapping_client.get(url)
    assert resp2.status_code == 200
    users = resp2.get_json()
    # 複数いる可能性もあるので any でチェック
    assert any(u["uuid"] == test_uuid for u in users)

    # (オプション) 大陸だけ指定しても見つかる
    url2 = f"/mapping/get_users?continent={test_cont}"
    resp3 = mapping_client.get(url2)
    assert resp3.status_code == 200
    users2 = resp3.get_json()
    assert any(u["uuid"] == test_uuid for u in users2)
