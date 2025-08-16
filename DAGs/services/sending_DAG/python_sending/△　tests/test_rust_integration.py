# D:\city_chain_project\network\DAGs\python\tests\test_rust_integration.py

"""
test_rust_integration.py (修正版)

Python <-> Rust 連携テスト: 
- Rustライブラリ(federation_dag)のimport
- ntru, dilithium stub呼び出し
- batch_verifyの並列検証
- バージョンなどの確認(例)
"""

import pytest

def test_federation_dag_import():
    import federation_dag
    api = federation_dag.RustDAGApi()
    assert api is not None

def test_version_check():
    """
    バージョン情報をRust側で返せるようにした例(実際にはlib.rsの#[pymodule]内で定義する必要)
    ここでは単に hasattr(...) で存在チェックするスタブ
    """
    import federation_dag
    assert hasattr(federation_dag, "__version__"), "Rust module should define __version__"

def test_ntru_dilithium():
    import federation_dag
    api = federation_dag.RustDAGApi()

    enc = api.ntru_encrypt_stub("hello")
    dec = api.ntru_decrypt_stub(enc)
    assert dec == "hello"

    sig = api.dilithium_sign_stub("testdata")
    ok = api.dilithium_verify_stub("testdata", sig)
    assert ok is True

def test_batch_verify_rayon():
    import federation_dag
    api = federation_dag.RustDAGApi()

    sample = [
        {"tx_id":"t1","sender":"Alice","receiver":"Bob","amount":10,"hash":"abcd"},
        {"tx_id":"t2","sender":"Charlie","receiver":"Dave","amount":20,"hash":"efgh"}
    ]
    verified = api.batch_verify(sample)
    # ダミーで all pass
    assert len(verified) == 2
    # etc.
