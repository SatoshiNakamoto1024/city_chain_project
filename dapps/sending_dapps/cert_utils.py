# File: dapps/sending_dapps/cert_utils.py
"""
証明書検証ユーティリティ（本番環境向け + テスト環境バイパス対応）

- CA ルート証明書（PEM）から NTRU ＋ Dilithium 用カスタム OID を読み取り、
  クライアント証明書を検証します。
- テスト環境（TEST_ENV=true）の場合は検証をスキップして常に True を返します。
"""

import os
import base64
import logging
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# pyasn1 周り
# ─────────────────────────────────────────────────────────────────────────────
# 「pyasn1-master」「pyasn1-modules-master」フォルダへのパス調整
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pyasn1-master"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pyasn1-modules-master"))

from pyasn1.codec.der import decoder as der_decoder, encoder as der_encoder
from pyasn1_modules import rfc5280
from pyasn1.type import univ

# ─────────────────────────────────────────────────────────────────────────────
# cryptography は PEM の妥当性チェックだけに使う（公開鍵抽出はしない）
# ここでは x509.load_pem_x509_certificate() のみ利用し、公開鍵取得は行いません。
# ─────────────────────────────────────────────────────────────────────────────
from cryptography import x509
from cryptography.hazmat.backends import default_backend

# ─────────────────────────────────────────────────────────────────────────────
# Dilithium 署名検証用ラッパーを import (PyO3 バインディング想定)
# 「dilithium-py」インストール先を sys.path に置く
sys.path.insert(0, r"D:\city_chain_project\ntru\dilithium-py")  # 実環境パスに合わせて調整
try:
    from app_dilithium import verify_message  # (msg: bytes, sig: bytes, pubkey: bytes) -> bool
except ImportError:
    # 本番環境では必ず動作するパスを通しておくこと！
    def verify_message(msg: bytes, sig: bytes, pubkey: bytes) -> bool:
        return False

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────
# カスタム OID 定義
# ─────────────────────────────────────────────────────────────────────────────
OID_NTRU_ALG    = "1.3.6.1.4.1.99999.1.0"    # NTRU 公開鍵 OID（例）
OID_DIL_SIG_ALG = "1.3.6.1.4.1.99999.1.100"  # Dilithium 署名アルゴリズム OID（例）

# ─────────────────────────────────────────────────────────────────────────────
# CA ルート証明書のパス
# （環境変数 CA_CERT_PATH が指定されていればそれを使い、なければデフォルト）
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_CA_PATH = Path(r"D:\city_chain_project\CA\certs\ca_root_20250503T080950Z.pem")
CA_CERT_PATH = Path(os.getenv("CA_CERT_PATH", str(DEFAULT_CA_PATH)))

# ─────────────────────────────────────────────────────────────────────────────
# CA ルート証明書の PEM／x509 Certificate オブジェクトをロード
# ─────────────────────────────────────────────────────────────────────────────
try:
    with open(CA_CERT_PATH, "rb") as f:
        _ca_pem = f.read()
    _ca_cert_obj = x509.load_pem_x509_certificate(_ca_pem, default_backend())
    logger.info(f"CA 証明書をロードしました: {CA_CERT_PATH}")
except FileNotFoundError:
    _ca_cert_obj = None
    _ca_pem = None
    logger.error(f"CA 証明書が見つかりません: {CA_CERT_PATH}")
except Exception as e:
    _ca_cert_obj = None
    _ca_pem = None
    logger.error(f"CA 証明書のロード中に例外: {e}")


def _pem_to_der(pem_bytes: bytes) -> bytes:
    """
    PEM → DER デコード
    -----BEGIN/END----- を取り除いて base64 をデコードして返却
    """
    lines = pem_bytes.splitlines()
    b64 = b"".join(line for line in lines if line and not line.startswith(b"-----"))
    return base64.b64decode(b64)


def _parse_cert(pem_bytes: bytes) -> rfc5280.Certificate:
    """
    pyasn1 モデルの Certificate にパースして返却
    """
    der = _pem_to_der(pem_bytes)
    cert, _ = der_decoder.decode(der, asn1Spec=rfc5280.Certificate())
    return cert


def extract_ntru_pub_from_spki(pem_bytes: bytes) -> bytes:
    """
    クライアント証明書（PEM）から NTRU 公開鍵を抽出。
    SPKI.algorithm.algorithm が OID_NTRU_ALG であることをチェックし、
    subjectPublicKey のバイト列を返却。
    """
    cert = _parse_cert(pem_bytes)
    spki = cert['tbsCertificate']['subjectPublicKeyInfo']
    alg_oid = str(spki['algorithm']['algorithm'])
    if alg_oid != OID_NTRU_ALG:
        raise ValueError(f"SPKI OID が NTRU ではありません: {alg_oid}")
    return bytes(spki['subjectPublicKey'].asOctets())


def extract_dilithium_pub_from_spki(pem_bytes: bytes) -> bytes:
    """
    クライアント証明書（PEM）の SPKI.algorithm.parameters に埋め込まれた
    Dilithium 公開鍵を取り出す。OctetString(DER)→生バイト列を返却。
    存在しなければ例外を投げる。
    """
    cert = _parse_cert(pem_bytes)
    alg = cert['tbsCertificate']['subjectPublicKeyInfo']['algorithm']
    params_any = alg.getComponentByName('parameters')
    if not (params_any and params_any.isValue):
        raise ValueError("SPKI.parameters に Dilithium 公開鍵が含まれていません")
    der_octet = bytes(params_any)  # DER-encoded OCTET STRING
    octet, _ = der_decoder.decode(der_octet, asn1Spec=univ.OctetString())
    return bytes(octet.asOctets())


def _load_ca_dilithium_pub() -> bytes:
    """
    CA ルート証明書 (_ca_pem) から Dilithium 公開鍵を一度だけ取り出す
    """
    if _ca_pem is None:
        raise FileNotFoundError("CA ルート証明書がロードされていません")
    return extract_dilithium_pub_from_spki(_ca_pem)


try:
    CA_DILITHIUM_PUB = _load_ca_dilithium_pub()
    logger.info("CA の Dilithium 公開鍵をロードしました。")
except Exception as e:
    CA_DILITHIUM_PUB = None
    logger.error(f"CA Dilithium 公開鍵のロード失敗: {e}")


def _is_test_env() -> bool:
    """
    環境変数 TEST_ENV をチェックし、テストモードかどうか返却
    """
    return os.getenv("TEST_ENV", "false").lower() in ("1", "true", "yes")


def verify_client_certificate(client_cert_pem: bytes) -> bool:
    """
    クライアント証明書 (PEM bytes) を次の手順で検証：
      1) SPKI.algorithm.algorithm が OID_NTRU_ALG かチェック → NTRU 公開鍵取得
      2) SPKI.algorithm.parameters から Dilithium 公開鍵取得
      3) 証明書の signatureAlgorithm が OID_DIL_SIG_ALG かチェック
      4) TBSCertificate 部分を DER 化して、CA_DILITHIUM_PUB で署名検証
    テスト環境 (TEST_ENV=true) なら常に True を返す。
    """
    if _is_test_env():
        return True

    if _ca_pem is None or CA_DILITHIUM_PUB is None:
        logger.error("CA 証明書または CA_DILITHIUM_PUB がロードされていないため検証できません")
        return False

    try:
        cert = _parse_cert(client_cert_pem)

        # 1) NTRU 公開鍵を抽出して OID チェック
        spki = cert['tbsCertificate']['subjectPublicKeyInfo']
        alg_oid = str(spki['algorithm']['algorithm'])
        if alg_oid != OID_NTRU_ALG:
            logger.error(f"クライアント証明書の OID が NTRU ではありません: {alg_oid}")
            return False

        # 2) Dilithium 公開鍵を抽出
        dil_pub = extract_dilithium_pub_from_spki(client_cert_pem)

        # 3) 証明書の署名アルゴリズム OID をチェック
        signature_alg_oid = str(cert['signatureAlgorithm']['algorithm'])
        if signature_alg_oid != OID_DIL_SIG_ALG:
            logger.error(f"証明書署名アルゴリズムが Dilithium ではありません: {signature_alg_oid}")
            return False

        # 4) TBSCertificate 部分を DER 化して、CA_DILITHIUM_PUB で署名検証
        tbs_der = der_encoder.encode(cert['tbsCertificate'])
        sig_bytes = bytes(cert['signature'].asOctets())

        valid = verify_message(tbs_der, sig_bytes, CA_DILITHIUM_PUB)
        if not valid:
            logger.error("Dilithium 署名検証に失敗しました")
            return False

        return True
    except Exception as e:
        logger.error(f"クライアント証明書検証例外: {e}")
        return False


def verify_message_signature(message: bytes, signature: bytes, pubkey_bytes: bytes) -> bool:
    """
    メッセージ署名検証 (Dilithium)。テスト環境 (TEST_ENV) の場合は True を返却。
    そうでなければ PyO3 版 verify_message() を呼び出す。
    """
    if _is_test_env():
        return True

    try:
        return verify_message(message, signature, pubkey_bytes)
    except Exception as e:
        logger.error(f"Dilithium メッセージ署名検証例外: {e}")
        return False
