# File: dapps/sending_dapps/cert_utils.py
"""
証明書検証ユーティリティ（本番環境向け + テスト環境モック対応）

- CA ルート証明書（PEM）から NTRU + Dilithium 用カスタム OID を読み取り、
  クライアント証明書を検証します。
- テスト環境では常に True を返すように切り替え可能です。
"""

import os
import base64
import logging
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# pyasn1 周り
# ─────────────────────────────────────────────────────────────────────────────
# pyasn1 / rfc5280 モジュールが project 直下の CA ディレクトリに置かれている想定です。
# 必要に応じて sys.path を調整してください。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pyasn1-master"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pyasn1-modules-master"))

from pyasn1.codec.der import decoder as der_decoder, encoder as der_encoder
from pyasn1_modules import rfc5280
from pyasn1.type import univ

# ─────────────────────────────────────────────────────────────────────────────
# cryptography（PEM → x509.Certificate）を使ってまず読み込みだけ行う
# ※ pyasn1 パースで失敗する場合、cryptography で PEM の妥当性確認を一度行う想定
# ─────────────────────────────────────────────────────────────────────────────
from cryptography import x509
from cryptography.hazmat.backends import default_backend

# ─────────────────────────────────────────────────────────────────────────────
# Dilithium 署名検証用ラッパー
# （外部の dilithium ライブラリ／PyO3 バインディングを想定）
# ─────────────────────────────────────────────────────────────────────────────
# 以下は dilithium-py 側の「verify_message(msg: bytes, sig: bytes, pubkey: bytes) -> bool」を import
sys.path.insert(0, r"D:\city_chain_project\ntru\dilithium-py")  # 例: dilithium-py のインストールパス
try:
    from app_dilithium import verify_message  # (msg, sig, pubkey) → bool
except ImportError:
    # 本番環境では必ず動作するようにパスを通してください。
    # テスト環境では下の verify_message() を直接 override します。
    def verify_message(msg: bytes, sig: bytes, pubkey: bytes) -> bool:
        return False

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────
# カスタム OID 定義
# ─────────────────────────────────────────────────────────────────────────────
OID_NTRU_ALG    = "1.3.6.1.4.1.99999.1.0"
OID_DIL_SIG_ALG = "1.3.6.1.4.1.99999.1.100"

# ─────────────────────────────────────────────────────────────────────────────
# CA ルート証明書のパス
# （環境変数 CA_CERT_PATH が指定されていればそれを使い、なければデフォルト）
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_CA_PATH = Path(r"D:\city_chain_project\CA\certs\ca_root_20250503T080950Z.pem")
CA_CERT_PATH = Path(os.getenv("CA_CERT_PATH", str(DEFAULT_CA_PATH)))

# ─────────────────────────────────────────────────────────────────────────────
# CA ルート証明書をロードし、<pem> と cryptography オブジェクトも保持
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
    PEM → DER。-----BEGIN/END----- を取り除いて base64 デコード。
    """
    lines = pem_bytes.splitlines()
    b64 = b"".join(line for line in lines if line and not line.startswith(b"-----"))
    return base64.b64decode(b64)

def _parse_cert(pem_bytes: bytes) -> rfc5280.Certificate:
    """
    pyasn1 モデルの Certificate にパースして返却。
    """
    der = _pem_to_der(pem_bytes)
    cert, _ = der_decoder.decode(der, asn1Spec=rfc5280.Certificate())
    return cert

def extract_ntru_pub_from_spki(pem_bytes: bytes) -> bytes:
    """
    クライアント証明書（PEM）から NTRU 公開鍵を抽出。
    SPKI.algorithm.algorithm が OID_NTRU_ALG であることを確認してから、
    subjectPublicKey のバイト列を返す。
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
    Dilithium 公開鍵を取り出す。存在しなければ例外を投げる。
    """
    cert = _parse_cert(pem_bytes)
    alg = cert['tbsCertificate']['subjectPublicKeyInfo']['algorithm']
    params_any = alg.getComponentByName('parameters')
    if not (params_any and params_any.isValue):
        raise ValueError("SPKI.parameters に Dilithium 公開鍵が含まれていません")
    # ANY＝OctetString(DER) として埋め込まれている想定 → もう一段デコード
    der_octet = bytes(params_any)   # これは DER エンコードされた OCTET STRING
    octet, _ = der_decoder.decode(der_octet, asn1Spec=univ.OctetString())
    return bytes(octet.asOctets())

def _load_ca_dilithium_pub() -> bytes:
    """
    CA ルート証明書 (_ca_pem) から Dilithium 公開鍵を一度だけ取り出す。
    """
    if _ca_pem is None:
        raise FileNotFoundError("CA ルート証明書がロードされていません")
    dil_pub = extract_dilithium_pub_from_spki(_ca_pem)
    return dil_pub

try:
    CA_DIL_PUB = _load_ca_dilithium_pub()
    logger.info("CA の Dilithium 公開鍵をロードしました。")
except Exception as e:
    CA_DIL_PUB = None
    logger.error(f"CA Dilithium 公開鍵のロード失敗: {e}")

def _is_test_env() -> bool:
    """
    環境変数 TEST_ENV をチェックして、テストモードかどうかを返す。
    """
    return os.getenv("TEST_ENV", "false").lower() in ("1", "true", "yes")

def verify_client_certificate(client_cert_pem: bytes) -> bool:
    """
    クライアント証明書（PEM バイト列）に対して以下を行う：
      1) SPKI.algorithm.algorithm が NTRU OID か確認 → NTRU 公開鍵取得
      2) SPKI.algorithm.parameters から Dilithium 公開鍵取得
      3) 証明書本体の署名アルゴリズムが OID_DIL_SIG_ALG か確認
      4) TBSCertificate 部分を DER 化して、CA_DIL_PUB で署名検証
    テスト環境（TEST_ENV=true）なら常に True を返す。
    """
    if _is_test_env():
        return True

    if _ca_pem is None or CA_DIL_PUB is None:
        logger.error("CA 証明書または CA_DIL_PUB がロードされていないため検証できません")
        return False

    try:
        cert = _parse_cert(client_cert_pem)

        # 1) NTRU 公開鍵を抽出して検証（OID チェックのみ）
        spki = cert['tbsCertificate']['subjectPublicKeyInfo']
        alg_oid = str(spki['algorithm']['algorithm'])
        if alg_oid != OID_NTRU_ALG:
            logger.error(f"クライアント証明書の OID が NTRU ではありません: {alg_oid}")
            return False
        # ntru_pub = bytes(spki['subjectPublicKey'].asOctets())  # 必要なら返り値として使う

        # 2) Dilithium 公開鍵を抽出
        dil_pub = extract_dilithium_pub_from_spki(client_cert_pem)

        # 3) 証明書の署名アルゴリズム OID を確認
        signature_alg_oid = str(cert['signatureAlgorithm']['algorithm'])
        if signature_alg_oid != OID_DIL_SIG_ALG:
            logger.error(f"証明書署名アルゴリズムが Dilithium ではありません: {signature_alg_oid}")
            return False

        # 4) TBSCertificate 部分を DER 化
        tbs_der = der_encoder.encode(cert['tbsCertificate'])
        sig_bytes = bytes(cert['signature'].asOctets())

        # 5) CA ルートの Dilithium 公開鍵で検証
        valid = verify_message(tbs_der, sig_bytes, CA_DIL_PUB)
        if not valid:
            logger.error("Dilithium 署名検証に失敗しました")
            return False

        return True
    except Exception as e:
        logger.error(f"クライアント証明書検証例外: {e}")
        return False

def verify_message_signature(message: bytes, signature: bytes, pubkey_bytes: bytes) -> bool:
    """
    Dilithium 署名検証（メッセージ + 署名 + 公開鍵）。
    テスト環境（TEST_ENV=true）なら常に True。
    そうでなければ app_dilithium.verify_message を呼び出す。
    """
    if _is_test_env():
        return True

    try:
        return verify_message(message, signature, pubkey_bytes)
    except Exception as e:
        logger.error(f"Dilithium メッセージ署名検証例外: {e}")
        return False
