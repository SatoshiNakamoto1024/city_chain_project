# municipality_registration/test_municipality_registration.py
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import uuid
import json
import boto3
import pytest

from municipality_registration.service import register_municipality
from municipality_registration.config import (
    MUNICIPALITY_TABLE,
    STAFF_TABLE,
    AWS_REGION,
    REGION_JSON
)

@pytest.fixture
def dynamodb():
    return boto3.resource("dynamodb", region_name=AWS_REGION)

@pytest.fixture
def sample_payload():
    return {
        "continent": "Europe",
        "country_code": "FR",
        "country_name": "France",
        "pref_code": "IDF",
        "pref_name": "Île-de-France",
        "municipality_name": f"Testville-{uuid.uuid4().hex[:6]}",
        "staff_email": "mayor@testville.fr",
        "staff_password": "password123"
    }

def test_register_municipality(dynamodb, sample_payload):
    muni_tbl  = dynamodb.Table(MUNICIPALITY_TABLE)
    staff_tbl = dynamodb.Table(STAFF_TABLE)

    # 1) 市町村登録 を実行
    res = register_municipality(sample_payload)
    assert res["success"] is True
    muni_id  = res["municipality_id"]
    staff_id = res["staff_id"]

    # 2) Municipalities テーブルにレコードが存在すること
    muni_item = muni_tbl.get_item(Key={
        "municipality_id":   muni_id,
        "municipality_name": sample_payload["municipality_name"]
    })
    assert "Item" in muni_item

    # 3) MunicipalStaffs テーブルに管理者レコードが存在すること
    staff_item = staff_tbl.get_item(Key={
        "staff_id":     staff_id,
        "municipality": muni_id
    })
    assert "Item" in staff_item

    # 4) region_tree.json 更新確認
    with open(REGION_JSON, encoding="utf-8") as f:
        region = json.load(f)
    cont = sample_payload["continent"]
    assert cont in region

    # 登録した市が JSON に反映されていること
    found = False
    for c in region[cont]["countries"]:
        for p in c["prefectures"]:
            if sample_payload["municipality_name"] in p["cities"]:
                found = True
    assert found, "登録した市町村が region_tree.json に反映されていません"
