vrf_leader (3) – リーダー選出
目的: VRF出力＋重み（stake/RTT/容量）で、1ラウンドの当選者・上位K候補・順位を決定（HRWのタイブレークにも）。
主API（ミックス）:

以下の構成で、Rust 側の VRF 拡張モジュールを pyo3／vrf クレート（Elliptic-Curve ECVRF）を使って実装します。OpenSSL の P-256 VRF（P256_SHA256_TAI）を利用します。

Algorithm/VRF/vrf_rust_src/
├── pyproject.toml
├── Cargo.toml
└── src/
    ├── lib.rs
    ├── keypair.rs
    ├── prover.rs
    └── verifier.rs


📦 使い方（インストール方法）
他の環境で使いたい場合： ※import pop_python でいけるので、他で使うってある？
pip install dist\vrf_python-0.1.0-py3-none-any.whl
pip install dist\vrf_rust-0.1.0-cp312-cp312-win_amd64.whl

# 統合テストエラー対応

(.venv312) D:\city_chain_project\Algorithm\VRF>pip list | findstr vrf
vrf_python                               0.1.0       D:\city_chain_project\Algorithm\VRF\vrf_python
vrf_rust                                 0.1.0       D:\city_chain_project\Algorithm\VRF\vrf_rust_src

ChatGPT said:
ありがとうございます。pip list | findstr vrf の結果を見る限り：

✅ 現在の状態
パッケージ名	バージョン	インストール元	状態
vrf_python	0.1.0	D:\city_chain_project\Algorithm\VRF\vrf_python	editable（OK）
vrf_rust	0.1.0	D:\city_chain_project\Algorithm\VRF\vrf_rust_src	OK

つまり、vrf_python は正しく -e . でインストールされているように見える 状態です。

🔍 それでも ModuleNotFoundError が出る原因（最有力）
✅ 解決方法：応急処置でテストを通すだけなら
set PYTHONPATH=D:\city_chain_project\Algorithm\VRF
pytest -v Algorithm/VRF/test_vrf_integration.py

あるいは test_vrf_integration.py 冒頭に
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent))
を一行書けば取り急ぎ動きます（ただし推奨はレイアウト修正）。

(.venv312) D:\city_chain_project\Algorithm\VRF>pytest -v test_vrf_integration.py
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 4 items

test_vrf_integration.py::test_end_to_end_roundtrip PASSED                                                        [ 25%]
test_vrf_integration.py::test_integration_negative_tampered_proof PASSED                                         [ 50%]
test_vrf_integration.py::test_integration_negative_wrong_pubkey PASSED                                           [ 75%]
test_vrf_integration.py::test_integration_string_message_support PASSED                                          [100%]

================================================== 4 passed in 0.45s ==================================================
