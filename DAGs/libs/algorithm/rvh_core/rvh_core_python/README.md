rvh_core (3) – HRW スコア
rvh_core/                               ← リポジトリ・ルート
├── README.md                      ← プロジェクト概要／ビルド手順
├── LICENSE                        ← Apache-2.0 など
├── .gitignore                     ← target/, __pycache__/ など
├── .github/                       ← CI/CD（後で GitHub Actions 設定を追加）
│   └── workflows/
│       └── ci.yml                 ← cargo test → maturin build → pytest
├── rvh_core_rust/                  ← Rust クレート（pyo3 + CLI）
│   ├── Cargo.toml                 ← crate-type = ["cdylib","rlib","bin"]
│   ├── pyproject.toml             ← maturin 用（wheel ビルド）
│   ├── benches/
│   │   └── bench_hwr_score.rs     ← criterion ベンチマーク
│   ├── examples/
│   │   └── cli_demo.rs            ← cargo run --example cli_demo
│   ├── src/
│   │   ├── lib.rs                 ← pub mod rendezvous; pub mod bindings;
│   │   ├── rendezvous.rs          ← HRW コア + Error 型
│   │   ├── bindings.rs            ← #[pymodule] ec_rust …
│   │   ├── main_rvh.rs            ← 小さな CLI (`cargo run --bin rvh`)
│   │   └── utils.rs               ← 共通ヘルパ（ハッシュ、SIMD 切替など）
│   └── tests/
│       ├── test_rvh_basic.rs      ← HRW 一意性・安定性
│       ├── test_import.rs         ← 単純import
│       ├── test_cli.rs            ← CLI encode/decode round-trip
│       └── test_py_bindings.rs    ← pyo3 経由で呼び出し
│ 
├── rvh_core_python/               ← Python “呼び出し側” パッケージ
│   ├── pyproject.toml             ← [build-system] hatchling / setuptools
│   ├── README.md                  ← pip install rvh_python
│   ├── rvh_core/                  ← import rvh_python as rvh
│   │   ├── __init__.py            ← from .vrh_builder import rendezvous_hash
│   │   ├── vrh_builder.py         ← Pure-Py fallback + Rust 呼び出し
│   │   ├── vrh_validator.py       ← 形式チェック／ベンチ補助
│   │   ├── app_rvh.py             ← typer / argparse CLI
│   │   └── _version.py            ← __version__ 自動生成
│   └── tests/
│       ├── test_builder_unit.py   ← Pure-Py 部分テスト
│       └── test_rvh_core.py       ← Rust バックエンド有無を切替
├── docs/
│   ├── architecture.md            ← HRW の数式と API 仕様
│   └── ffi_layout.md              ← Python↔Rust 型マップ
└── build.rs                       ← （必要なら）ビルド時生成コード


2️⃣ rvh_python/__init__.py を修正
# Algorithm/RVH/rvh_python/__init__.py
"""
rvh_python パッケージ
Python ネイティブ版 + Rust バックエンドを透過的に扱うレイヤ
"""

# vrh_builder を読み込んで公開
from . import vrh_builder           # noqa: F401

# 使い勝手用にトップレベル re-export
from .vrh_builder import (
    rendezvous_hash,
    RVHError,
)

__all__: tuple[str, ...] = (
    "rendezvous_hash",
    "RVHError",
)

これで from rvh_python import vrh_builder
あるいは from rvh_python import rendezvous_hash が両方とも通るようになります。

3️⃣ editable install を忘れずに
cd Algorithm/RVH/rvh_python
pip uninstall -y rvh_python          # 古い失敗分を削除
pip install -e .
これをしないと pytest のときに rvh_python がパスに入らず、再び ImportError になります。

#　wheel を dist\ に置きたいなら
python -m build --wheel --outdir dist（Python ラッパも含め全部）


#　テスト方法
# CLI 動作確認
# 同期 API
python -m rvh_core.app_rvh -n n1,n2,n3 --name demo --count 2

# 非同期 API
python -m rvh_core.app_rvh -n n1,n2,n3 --key demo -c 2 --async

# --level は受け取るだけ（互換用）
python -m rvh_core.app_rvh -n a,b,c --name obj --count 1 --level debug

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python>python -m rvh_core.app_rvh -n n1,n2,n3 --name demo --count 2
['n1', 'n2']

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python>python -m rvh_core.app_rvh -n n1,n2,n3 --key demo -c 2 --async
Executing <Task pending name='Task-1' coro=<arendezvous_hash() running at D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\rvh_core\rvh_builder.py:107> wait_for=<Future pending cb=[<builtins.PyDoneCallback object at 0x000001D75B2AEF70>(), Task.task_wakeup()] created at D:\Python\Python312\Lib\asyncio\base_events.py:448> cb=[_run_until_complete_cb() at D:\Python\Python312\Lib\asyncio\base_events.py:181] created at D:\Python\Python312\Lib\asyncio\runners.py:100> took 0.110 seconds
['n1', 'n2']

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python>python -m rvh_core.app_rvh -n a,b,c --name obj --count 1 --level debug
['a']


# 単体テスト
$ pytest rvh_core/tests -q
printを表示させたいなら
　pytest rvh_core/tests/test_builder_unit.py -s

# ③ テストファイルは「絶対パス」で実行
NGな例（相対パス）
pytest -v test_rvh.py

OKな例（絶対パス）
pytest -v rvh_core_python/tests
あるいはプロジェクトルート（D:\city_chain_project\）に移動してから実行：
cd D:\city_chain_project
pytest -v Algorithm/RVH/rvh_python/test_rvh.py

落ち着いて、いま起きていることを一枚の図にして整理します。
Algorithm/
└─ RVH/
   └─ rvh_python/
      ├─ __init__.py   ← ここから .rvh_builder を import している
      ├─ rvh_builder.py ← ★ これが実際に無い or 名前が違う
      └─ test_rvh.py   ← pytest がここを読み込む
① pytest が探すモジュールの流れ
test_rvh.py を読み込む

そこで import rvh_python

rvh_python/__init__.py が実行される

from .rvh_builder import … を実行しようとする

rvh_python フォルダー内に rvh_builder.py（または同名の .pyd）が無い

⇒ ModuleNotFoundError: No module named 'rvh_python.rvh_builder'

エラーは 5. で確実に起きています。

② 何を確認すればいいか
チェックポイント	期待される状態
A. ファイル名	rvh_python/rvh_builder.py が実在するか？（拡張子まで正確に）
B. 大文字小文字	Windows でもモジュール名は大小区別するので rvh_builder.py であること
C. __init__.py	相対 import を使っているか：
from .rvh_builder import rendezvous_hash, RVHError
D. current dir	今コマンドを打っている場所が Algorithm/ の下 か
（rootdir が D:\city_chain_project と表示されているので OK）
E. パッケージ再インストール不要	編集後はただ pytest を実行するだけで良い（editable インストールを消しても構わない）


# test が成功したら、buildをしてdist¥に配布物を吐き出す
プロジェクトルートでビルド実行
# Algorithm/RVH/rvh_python ディレクトリで
python -m build
成功すると、
dist/
  rvh_python-0.1.0-py3-none-any.whl
  rvh_python-0.1.0.tar.gz
が生成されます。