# registration/test_registration.py
# -*- coding: utf-8 -*-
"""
tests/test_registration.py

integration‑test  (PEM 運用 + NTRU & Dilithium 検証版)
------------------------------------------------------
フロー
------
1) /registration/  ─ 新規登録（PEM はサーバ側で生成）
2) 指紋・公開鍵抽出・Dilithium 署名検証
3) pairing_token → 追加端末登録（同上の検証を実施）
"""

import os
import sys
import json
import base64
import uuid
import hashlib
import time
from datetime import datetime, timezone

import requests
import boto3
import pytest

# ---------------------------------------------------------------------------
# Python パス設定
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from registration.config import AWS_REGION
from auth_py.fingerprint import normalize_fp

# クライアント証明書パーサ & 署名検証ユーティリティ
from auth_py.client_cert.dilithium_verify import (
    extract_ntru_pub_from_spki,
    extract_dilithium_pub_from_spki,
    verify_pem,
)

# ---------------------------------------------------------------------------
# 固定 URL
# ---------------------------------------------------------------------------
BASE_URL  = "http://127.0.0.1:5000"
REG_URL   = f"{BASE_URL}/registration/"
TOKEN_URL = f"{BASE_URL}/registration/pairing_token"
ADD_DEV   = REG_URL   # qr_code 付き POST は /registration/ で端末追加

# ---------------------------------------------------------------------------
# DynamoDB (ローカル or AWS)
# ---------------------------------------------------------------------------
dynamodb      = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table   = dynamodb.Table("UsersTable")
devices_table = dynamodb.Table("DevicesTable")

# ---------------------------------------------------------------------------
# DynamoDB クリーンアップ
# ---------------------------------------------------------------------------
def _scan_and_delete(table, filt_kw):
    last = None
    while True:
        if last:
            filt_kw["ExclusiveStartKey"] = last
        resp = table.scan(**filt_kw)
        for itm in resp.get("Items", []):
            key = {e["AttributeName"]: itm[e["AttributeName"]] for e in table.key_schema}
            table.delete_item(Key=key)
        last = resp.get("LastEvaluatedKey")
        if not last:
            break

def cleanup_user(username: str):
    _scan_and_delete(
        users_table,
        {
            "FilterExpression": "#u = :u",
            "ExpressionAttributeNames": {"#u": "username"},
            "ExpressionAttributeValues": {":u": username},
        },
    )

def cleanup_devices(uuid_val: str):
    _scan_and_delete(
        devices_table,
        {
            "FilterExpression": "#u = :u",
            "ExpressionAttributeNames": {"#u": "uuid"},
            "ExpressionAttributeValues": {":u": uuid_val},
        },
    )

# ---------------------------------------------------------------------------
# PEM / Finger‑Print ヘルパ
# ---------------------------------------------------------------------------
def calc_fp_from_pem(pem_str: str) -> str:
    return normalize_fp(hashlib.sha256(pem_str.encode()).hexdigest())

def _assert_cert_integrity(pem_b64: str, expected_fp: str | None = None):
    """PEM(base64) が NTRU/Dilithium を格納し署名が正しいか確認"""
    pem_bytes = base64.b64decode(pem_b64)
    pem_str   = pem_bytes.decode()

    # 指紋
    fp = calc_fp_from_pem(pem_str)
    if expected_fp:
        assert fp == normalize_fp(expected_fp)

    # 公開鍵抽出
    ntru_pub = extract_ntru_pub_from_spki(pem_bytes)
    dil_pub  = extract_dilithium_pub_from_spki(pem_bytes)
    assert ntru_pub and dil_pub, "公開鍵抽出失敗"

    # Dilithium 署名検証
    assert verify_pem(pem_bytes), "Dilithium 署名検証失敗"

# ---------------------------------------------------------------------------
# 登録ユーティリティ
# ---------------------------------------------------------------------------
def primary_register() -> dict:
    username  = "it_parent_" + uuid.uuid4().hex[:6]
    cleanup_user(username)

    payload = {
        "username": username,
        "email":    "parent@example.com",
        "password": "TestPass123!",
        "name":      "Primary User",
        "birth_date": "2000-01-01",
        "address":    "Primary Street",
        "mynumber":   "987654321098",
        "phone":      "08011112222",
        "initial_harmony_token": "100",
    }
    r = requests.post(REG_URL, json=payload, timeout=30)
    assert r.status_code == 200, f"registration failed: {r.text}"
    body = r.json()
    assert body.get("success") is True

    return {
        "username":    username,
        "password":    payload["password"],
        "uuid":        body["uuid"],
        "fingerprint": body["fingerprint"],
        "client_cert": body["client_cert"],
    }

RETRY, SLEEP = 10, 2

def issue_pairing_token(username: str, password: str, fp: str):
    req = {
        "username":       username,
        "password":       password,
        "client_cert_fp": fp,
    }
    last = None
    for _ in range(RETRY):
        last = requests.post(TOKEN_URL, json=req, timeout=15)
        if last.status_code == 200:
            break
        time.sleep(SLEEP)
    assert last.status_code == 200, f"token issue failed: {last.text}"
    data = last.json()
    qr_b64 = base64.b64encode(json.dumps(data).encode()).decode()
    return data, qr_b64

def register_secondary(qr_b64: str, username: str, password: str):
    payload = {
        "qr_code":  qr_b64,
        "username": username,
        "password": password,
        "device_name": "SecDevice",
    }
    r = requests.post(ADD_DEV, json=payload, timeout=30)
    assert r.status_code == 200, f"secondary reg failed: {r.text}"
    return r.json()

# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------
def test_get_register_html():
    res = requests.get(REG_URL, timeout=10)
    assert res.status_code == 200
    assert "ユーザー登録" in res.text

def test_primary_registration_and_cert():
    info = primary_register()

    # PEM & Finger‑Print 整合性 + 鍵抽出 + 署名検証
    _assert_cert_integrity(info["client_cert"], info["fingerprint"])

def test_pairing_token_flow_and_add_device():
    info = primary_register()
    time.sleep(2)  # DynamoDB の整合性待ち（ローカルスタック用）

    token_obj, qr_b64 = issue_pairing_token(
        info["username"], info["password"], info["fingerprint"]
    )
    add = register_secondary(qr_b64, info["username"], info["password"])

    # 追加端末 PEM 検査
    _assert_cert_integrity(add["client_cert"], add["fingerprint"])

    # 同じユーザ UUID で device が 2 件以上あることを確認
    scan = devices_table.scan(
        FilterExpression="#u = :u",
        ExpressionAttributeNames={"#u": "uuid"},
        ExpressionAttributeValues={":u": info["uuid"]},
        ConsistentRead=True,
    )
    assert len(scan["Items"]) >= 2
    assert any(i["device_id"] == add["device_id"] for i in scan["Items"])

def test_pairing_token_invalid_or_tampered():
    info = primary_register()
    time.sleep(2)

    _, qr_b64 = issue_pairing_token(
        info["username"], info["password"], info["fingerprint"]
    )

    # 1) 期限切れ改竄
    bad = json.loads(base64.b64decode(qr_b64))
    bad["expires_at"] = int(time.time()) - 10
    qr_bad = base64.b64encode(json.dumps(bad).encode()).decode()

    r1 = requests.post(ADD_DEV, json={
        "qr_code": qr_bad,
        "username": info["username"],
        "password": info["password"],
    }, timeout=15)
    assert r1.status_code in (400, 401, 500)

    # 2) トークン改竄
    bad2 = json.loads(base64.b64decode(qr_b64))
    bad2["device_token"] = uuid.uuid4().hex
    qr_bad2 = base64.b64encode(json.dumps(bad2).encode()).decode()

    r2 = requests.post(ADD_DEV, json={
        "qr_code": qr_bad2,
        "username": info["username"],
        "password": info["password"],
    }, timeout=15)
    assert r2.status_code in (400, 401, 500)

def test_registration_post_validation_errors():
    # ボディ無し
    r = requests.post(REG_URL, timeout=10)
    assert r.status_code == 400

    # 必須欠落
    r2 = requests.post(REG_URL, json={"username": "x"}, timeout=10)
    assert r2.status_code in (400, 500)
