# login_app/cert_checker.py
"""
cert_checker.py
─────────────────────────────────────────────
登録時に保存された証明書メタと、ログイン時に送られてくる
client_cert(Base64(JSON)) を突き合わせて検証する。
"""
from __future__ import annotations
import sys, os, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import base64
import json
import logging
import requests

from auth_py.fingerprint import calc_fp_from_pem, normalize_fp
from login_app.config    import CLIENT_CERT_ENDPOINT


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ───────────────────────── internal helpers ─────────────────────────
def _extract_fp_candidates(cert_json: dict) -> tuple[str, str]:
    """
    返り値は `(fp_from_field, fp_from_pem)` のタプル。

    * fp_from_field … cert_json["fingerprint"] があれば normalize して返す。
                      無ければ ""。
    * fp_from_pem   … cert_json["pem"] から calc_fp_from_pem() した値。
                      pem が無い場合は ""。
    """
    fp_field = normalize_fp(cert_json["fingerprint"]) if "fingerprint" in cert_json else ""
    fp_pem   = calc_fp_from_pem(cert_json["pem"])     if "pem"        in cert_json else ""
    return fp_field, fp_pem


def _fp_set_from_b64(b64_json: str) -> set[str]:
    try:
        decoded = base64.b64decode(b64_json).decode("utf-8")
        cert_json = json.loads(decoded)
        fps = _extract_fp_candidates(cert_json)
        return {fp for fp in fps if fp}
    except Exception as e:
        raise
    

def _stored_fp_set(cert_meta: dict) -> set[str]:
    """
    UsersTable に保存されている certificate メタから、
    ・fingerprint フィールド
    ・client_cert(Base64) 内の 2 種候補
    をまとめて set で返す。
    """
    fps: set[str] = set()

    if "fingerprint" in cert_meta:
        fps.add(normalize_fp(cert_meta["fingerprint"]))

    if "client_cert" in cert_meta:
        try:
            fps |= _fp_set_from_b64(cert_meta["client_cert"])
        except Exception:
            pass  # 保存済 client_cert が壊れていても無視

    return fps


# ───────────────────────── public entry point ───────────────────────
def verify_certificate(user_item: dict, cert_b64: str) -> None:
    """
    * client_cert(Base64) の fingerprint 候補集合
    * UsersTable 側に保持している fingerprint 候補集合
    の **積集合が空でなければ OK** と判定する。

    失効フラグの確認（ローカル & オンライン）も行う。
    """
    try:
        presented_fps = _fp_set_from_b64(cert_b64)
    except Exception as e:
        raise ValueError(f"client_cert malformed ({e})") from e

    if not presented_fps:
        raise ValueError("unable to derive fingerprint from client_cert")

    stored_fps = _stored_fp_set(user_item.get("certificate") or {})
    
    if presented_fps.isdisjoint(stored_fps):
        logger.debug("cert FP mismatch: presented=%s stored=%s",
                     presented_fps, stored_fps)
        raise ValueError("certificate fingerprint mismatch")
    
    print("### DEBUG  presented:", presented_fps)
    print("### DEBUG  stored   :", stored_fps)
    print("### DEBUG  diff     :", presented_fps.symmetric_difference(stored_fps))
    
    # ── revoked flag（ローカル） ──────────────────────────────────
    if (user_item.get("certificate") or {}).get("revoked"):
        raise ValueError("certificate already revoked")

    # ── online revocation check（best effort） ───────────────────
    try:
        res = requests.get(
            CLIENT_CERT_ENDPOINT.replace("/client_cert", "/check_cert"),
            params={"uuid": user_item["uuid"]},
            timeout=3,
        )
        res.raise_for_status()
        if res.json().get("revoked"):
            raise ValueError("certificate is revoked (online)")
    except requests.RequestException as e:
        logger.warning("revocation check skipped: %s", e)

    # all green
    return
