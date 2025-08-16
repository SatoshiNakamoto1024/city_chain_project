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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mapping_continental_municipality.config   import USER_LOCATION_TABLE, AWS_REGION
from mapping_continental_municipality.services import set_user_location_mapping, get_users_by_location
from mapping_continental_municipality.app_mapping_municipality import create_mapping_app

@pytest.fixture(scope="session")
def dynamodb_resource():
    return boto3.resource("dynamodb", region_name=AWS_REGION)

@pytest.fixture(scope="session")
def user_location_table(dynamodb_resource):
    return dynamodb_resource.Table(USER_LOCATION_TABLE)

def test_services_set_and_get(user_location_table):
    """
    1) set_user_location_mapping でレコードを書き込み
    2) get_users_by_location で正しく取得できるかを検証
    3) 再度 set_user_location_mapping を呼び、古いマッピングが削除されたかチェック
    """
    test_uuid     = "test-" + str(uuid.uuid4())[:8]
    test_cont1    = "Cont1"
    test_country1 = "C1"
    test_pref1    = "P1"
    test_muni1    = "Muni1"

    # 末尾に新しいマッピングで上書き用のデータ
    test_cont2    = "Cont2"
    test_country2 = "C2"
    test_pref2    = "P2"
    test_muni2    = "Muni2"

    # 事前に削除（古いレコードが残っていても問題ないように）
    try:
        # 古い形式の SK = "C1#P1#Muni1#test_uuid"
        old_sk = f"{test_country1}#{test_pref1}#{test_muni1}#{test_uuid}"
        user_location_table.delete_item(Key={"continent": test_cont1, "location_uuid": old_sk})
    except Exception:
        pass
    try:
        # 2 回目の SK = "C2#P2#Muni2#test_uuid"
        new_sk = f"{test_country2}#{test_pref2}#{test_muni2}#{test_uuid}"
        user_location_table.delete_item(Key={"continent": test_cont2, "location_uuid": new_sk})
    except Exception:
        pass

    # 1) サービス関数で書き込み（version1）
    set_user_location_mapping(test_uuid, test_cont1, test_country1, test_pref1, test_muni1)

    # 書き込み直後、get_item で確認
    resp1 = user_location_table.get_item(Key={"continent": test_cont1,
                                              "location_uuid": f"{test_country1}#{test_pref1}#{test_muni1}#{test_uuid}"})
    item1 = resp1.get("Item")
    assert item1 is not None
    assert item1["continent"] == test_cont1
    assert item1["country"] == test_country1

    # 2) get_users_by_location で取得できるか
    users1 = get_users_by_location(test_cont1)
    assert any(u["uuid"] == test_uuid for u in users1)

    # 3) 同じ UUID で別地域に上書き
    set_user_location_mapping(test_uuid, test_cont2, test_country2, test_pref2, test_muni2)

    # 「旧」レコードが削除されていること
    resp_old = user_location_table.get_item(Key={"continent": test_cont1,
                                                 "location_uuid": f"{test_country1}#{test_pref1}#{test_muni1}#{test_uuid}"})
    assert "Item" not in resp_old or resp_old.get("Item") is None

    # 「新」レコードが存在すること
    resp_new = user_location_table.get_item(Key={"continent": test_cont2,
                                                 "location_uuid": f"{test_country2}#{test_pref2}#{test_muni2}#{test_uuid}"})
    item2 = resp_new.get("Item")
    assert item2 is not None
    assert item2["continent"] == test_cont2
    assert item2["country"] == test_country2

    # get_users_by_location も version2 で取得可能か確認
    users2 = get_users_by_location(test_cont2)
    assert any(u["uuid"] == test_uuid for u in users2)


@pytest.fixture
def mapping_app():
    app = create_mapping_app()
    app.testing = True
    return app

@pytest.fixture
def mapping_client(mapping_app):
    return mapping_app.test_client()

def test_routes_set_and_get(mapping_client, user_location_table):
    """
    1) /mapping/set_mapping (POST) でレコードを書き込み
    2) /mapping/get_users (GET) で取得できるか検証
    """
    test_uuid     = "route-" + str(uuid.uuid4())[:8]
    test_cont     = "RTC"
    test_country  = "RTC"
    test_pref     = "RTP"
    test_muni     = "RTMuni"

    # 事前に削除
    test_sk = f"{test_country}#{test_pref}#{test_muni}#{test_uuid}"
    try:
        user_location_table.delete_item(Key={"continent": test_cont, "location_uuid": test_sk})
    except Exception:
        pass

    # 1) /mapping/set_mapping を呼び出し
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
    url = f"/mapping/get_users?continent={test_cont}&country={test_country}&prefecture={test_pref}&municipality={test_muni}"
    resp2 = mapping_client.get(url)
    assert resp2.status_code == 200
    users = resp2.get_json()
    assert any(u["uuid"] == test_uuid for u in users)

    url2 = f"/mapping/get_users?continent={test_cont}"
    resp3 = mapping_client.get(url2)
    assert resp3.status_code == 200
    users2 = resp3.get_json()
    assert any(u["uuid"] == test_uuid for u in users2)
