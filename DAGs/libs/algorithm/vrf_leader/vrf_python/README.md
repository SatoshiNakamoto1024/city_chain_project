# vrf_python

VRF (Verifiable Random Function) の Python クライアントラッパーです。
内部で Rust 製の `vrf_rust` 拡張モジュールを呼び出して、鍵生成・証明生成・検証を行います。

1. 背景：VRF とは何か？
Verifiable Random Function (VRF) は、擬似乱数を生成しつつ、その出力が正しく当該秘密鍵所有者によって算出されたものであることを誰でも検証できる仕組みです。
主にブロックチェーンや分散システムにおける「公平なリーダー選出」や「シャード分配のランダム化」に用いられます。
本実装では、OpenSSL 上の ECVRF（楕円曲線 P-256 + SHA256 による VRF）を用いています。
Rust 側で安全かつ高速に VRF を扱い、そのバイナリ出力を Python から簡単に呼び出せるようにしたのがこのパッケージです。

2. 提供 API
2.1. 鍵ペア生成：generate_keypair()
from vrf_python.vrf_builder import generate_keypair
pub_hex, priv_hex = generate_keypair()

戻り値
pub_hex：公開鍵（P-256 上の点）を 16 進文字列にしたもの
priv_hex：秘密鍵（スカラー値）を 16 進文字列にしたもの

内部では Rust の generate_vrf_keypair_py() を呼び出し、
返ってきた Vec<u8>（Python では list[int]）を確実に bytes に変換して .hex() しています。

2.2. VRF 証明（Proof）とハッシュ出力：prove_vrf()
from vrf_python.vrf_builder import prove_vrf
proof_hex, hash_hex = prove_vrf(priv_hex, b"some message")

# または文字列も可
proof_hex, hash_hex = prove_vrf(priv_hex, "some message")

引数
secret_key_hex：上で取得した秘密鍵の 16 進文字列
message：bytes または str

戻り値
proof_hex：VRF 証明（π）を 16 進文字列にしたもの
hash_hex：証明から導出されるハッシュ出力（β）を 16 進文字列にしたもの
内部では Rust の prove_vrf_py() を呼び出し、2 つの出力（証明とハッシュ）それぞれを _ensure_bytes で bytes 化し、.hex() をかけています。

2.3. VRF 証明の検証：verify_vrf()
from vrf_python.vrf_validator import verify_vrf
hash_hex = verify_vrf(pub_hex, proof_hex, b"some message")

# or
hash_hex = verify_vrf(pub_hex, proof_hex, "some message")

引数
public_key_hex：公開鍵の 16 進文字列
proof_hex：VRF 証明の 16 進文字列
message：元のメッセージ（bytes or str）

戻り値
hash_hex：検証に成功すると同じハッシュ（β）が 16 進文字列で返ります。
もし証明が改ざんされていたり、鍵／メッセージが合わない場合は内部で例外が投げられます。

3. データ型変換のポイント
Rust の PyO3 バインディングからは Vec<u8> が Python では list[int] として見えることがあります。
このまま binascii.hexlify() に渡すと「bytes-like object is required, not 'list'」というエラーになるため、
_ensure_bytes() ヘルパーを必ず通し、bytes(data) で固めてから .hex() しています。
def _ensure_bytes(data):
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, list):
        return bytes(data)
    raise TypeError(...)

4. 実際のワークフロー例
from vrf_python.vrf_builder import generate_keypair, prove_vrf
from vrf_python.vrf_validator import verify_vrf

# 1) 鍵ペア生成
pub_hex, priv_hex = generate_keypair()
print("Public Key :", pub_hex)
print("Secret Key :", priv_hex)

# 2) メッセージに対する VRF 証明とハッシュを生成
message = b"hello vrf"
proof_hex, hash_out1 = prove_vrf(priv_hex, message)
print("Proof      :", proof_hex)
print("Hash       :", hash_out1)

# 3) 証明の検証
hash_out2 = verify_vrf(pub_hex, proof_hex, message)
assert hash_out1 == hash_out2
print("検証 OK！ Hash 一致 →", hash_out2)

5. まとめ
generate_keypair() で公開鍵・秘密鍵を Hex 文字列として取得
prove_vrf() で任意のメッセージに対する VRF 証明とハッシュを取得
verify_vrf() で誰でもその証明が正当であることを検証し、同じハッシュを得る

これにより、分散システムの公正なリーダー選出やシャード分配などに使える安全なランダムネス基盤が Python から簡単に扱えるようになります。ぜひご活用ください！


## インストール

```bash
# 事前に vrf_rust をインストール済みであること
pip install vrf_rust
# 本パッケージを editable モードでインストール
pip install -e .


# 使い方
キーペア生成
from vrf_python import generate_keypair

pk_hex, sk_hex = generate_keypair()
print("PK:", pk_hex)
print("SK:", sk_hex)

証明生成
from vrf_python import prove_vrf

proof_hex, hash_hex = prove_vrf(sk_hex, b"hello")
print("Proof:", proof_hex)
print("Hash:", hash_hex)

検証
from vrf_python import verify_vrf

hash2 = verify_vrf(pk_hex, proof_hex, b"hello")
assert hash2 == hash_hex

CLI デモ
python app_vrf.py gen
python app_vrf.py prove <sk_hex> "message"
python app_vrf.py verify <pk_hex> <proof_hex> "message"

テスト
pytest test_vrf.py


### 3. VRF/vrf_python/__init__.py
"""
vrf_python package
"""
from .vrf_builder import generate_keypair, prove_vrf
from .vrf_validator import verify_vrf

__all__ = ["generate_keypair", "prove_vrf", "verify_vrf"]


# test
(.venv312) D:\city_chain_project\Algorithm\VRF\vrf_python>pytest -v test_vrf.py
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 2 items

test_vrf.py::test_roundtrip PASSED                                                                               [ 50%]
test_vrf.py::test_bad_proof PASSED                                                                               [100%]

================================================== 2 passed in 0.09s ==================================================

# test が成功したら、buildをしてdist¥に配布物を吐き出す
プロジェクトルートでビルド実行
# Algorithm/VRF/vrf_python ディレクトリで
python -m build
成功すると、
dist/
  vrf_python-0.1.0-py3-none-any.whl
  vrf_python-0.1.0.tar.gz
が生成されます。
