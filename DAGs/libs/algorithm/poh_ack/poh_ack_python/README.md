poh_ack/
├── README.md
├── LICENSE                         # → Apache‑2.0 などを配置
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml                  # Rust→maturin→pytest 一気通し CI
│
├── poh_ack_rust/                   # Rust コア & PyO3 バインディング
│   ├── Cargo.toml
│   ├── pyproject.toml              # maturin build 設定（abi3‑py312）
│   ├── build.rs
│   ├── benches/
│   │   └── bench_verifier.rs
│   ├── src/
│   │   ├── lib.rs
│   │   ├── ackset.rs
│   │   ├── main_ack.rs
│   │   ├── verifier.rs            # 署名・TTL 検証ロジック
│   │   ├── ttl.rs                 # TTL helper
│   │   ├── error.rs
│   │   └── bindings.rs            # #[pymodule] & #[pyfunction]
│   └── tests/
│       ├── test_cli.rs
│       ├── test_ackset.rs
│       ├── test_verifier.rs
│       └── test_py_bindings.rs
│
└── poh_ack_python/                 # Python ラッパ & ユーティリティ
    ├── pyproject.toml              # Hatch(PEP‑621) でビルド
    ├── README.md
    └── poh_ack/
        ├── __init__.py
        ├── _version.py
        ├── cli.py                  # エンドポイント
        ├── models.py               # Pydantic v2: AckRequest / AckResult
        ├── verifier.py             # async FFI + フォールバック pure‑py
        └── tests/
            ├── __init__.py
            ├── test_verifier.py
            └── test_ttl.py

📦 models.py：データモデル
■　AckRequest
入力データ構造体
フィールド：
id（トランザクションID）
timestamp（RFC3339 文字列）
signature（Base58-encoded Ed25519署名）
pubkey（Base58-encoded Ed25519公開鍵）

■　AckResult
検証結果構造体
フィールド：
id：もとのトランザクションID
valid：True=検証OK / False=NG
error：失敗時のエラーメッセージ（または None）
Pydantic v2 による型チェックとバリデーションを自動で行い、安心して受け渡し可能です。

🔍 verifier.py：検証ロジック
1. Rust拡張（poh_ack_rust）との連携
ビルド済みの PyO3 モジュールがインストールされていれば、それを優先的に呼び出します。
同期版：rust_ack.verify(ttl_seconds)
非同期版：await rust_ack.verify_async(ttl_seconds)
Rustコアによる ed25519 署名＆TTL検証はネイティブ実装なので高速です。

2. Pure‑Python フォールバック
Rust拡張が無い環境でも動くよう、以下を純Pythonで実装：
・TTLチェック
timestamp を datetime.fromisoformat でパース
UTC現在時刻と比較し、期限超過ならエラー
・Ed25519署名検証
cryptography ライブラリの Ed25519PublicKey を利用
Base58→バイト列をデコードし、pubkey.verify で検証
コード中の _canonical_payload 関数は Rust とまったく同じ “{"id":"…","timestamp":"…"}” のバイト列を組み立て、一貫性を担保しています。

3. API
from poh_ack.models import AckRequest
from poh_ack.verifier import verify_ack, verify_ack_async

req = AckRequest(
    id="tx123",
    timestamp="2025-07-28T12:34:56Z",
    signature="…",
    pubkey="…",
)

# 同期検証
res = verify_ack(req, ttl_seconds=300)
print(res.valid, res.error)

# 非同期検証
import asyncio
res2 = asyncio.run(verify_ack_async(req, 300))
print(res2.valid, res2.error)

💻 cli.py：コマンドラインインターフェース
Click を使った２つのサブコマンドを提供：
poh-ack verify
poh-ack verify --input path/to/ack.json --ttl 300
JSONファイルを読み込み、同期的に検証。
結果は JSON 文字列で標準出力へ。

poh-ack verify-async
poh-ack verify-async --input path/to/ack.json --ttl 300
非同期検証を行い、同様に結果を出力。
大量バッチや GUI/ウェブ連携時にも使いやすいモードです。

✅ テスト（tests/）
test_verifier.py
Rust／Pure‑Python 両モードで同期⇔非同期検証をチェック
test_ttl.py
TTLのみの有効／期限切れ検証フォールバックを単独テスト
どちらも pytest／pytest-asyncio で一発パス。CIにも組み込み済みです。

🎯 まとめ
Rust 拡張＋Pure‑Python フォールバック で、どの環境でも動作
同期・非同期 API を一貫したインターフェースで提供
CLI ですぐに使えるスクリプトが付属
Pydantic モデル でリクエスト・レスポンスを型安全に
このように、poh_ack_python は PoH‑ACK の署名＆TTL検証を、あらゆる環境・ワークフローで利用できるように設計された汎用ライブラリ＆ツール群です。ぜひプロダクションにもご活用ください！



#　1. WSL のセットアップ
/ 4.24.4 ソースを C 拡張スキップ でビルド
pip uninstall -y protobuf
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
pip install protobuf==5.27.0
REM ↑ 変数のおかげでランタイムでは純 Python 実装のみロードされる
手元で wheel をビルドしないので Visual C++ エラーは出ない

WSL の有効化
管理者 PowerShell を開き、以下を実行：
PS C:\WINDOWS\system32> wsl --install

これで既定のディストリビューション（Ubuntu）がインストールされ、再起動後にユーザー設定（UNIX ユーザー名／パスワード）を求められます。

Ubuntu の起動
スタートメニューから「Ubuntu」を起動。
sudo apt update && sudo apt upgrade -y
PW: greg1024

(よく切れるので、切れたらこれをやる)
# 1) ビジーでも強制的にアンマウント
deactivate          # venv を抜ける
sudo umount -l /mnt/d      # ← l (エル) オプション
# 2) 改めて Windows の D: をマウント
sudo mount -t drvfs D: /mnt/d -o metadata,uid=$(id -u),gid=$(id -g)

Python3.12 のインストール
Ubuntu のリポジトリによっては最新が入っていないので、deadsnakes PPA を追加しておくと便利です：
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv
sudo apt install python3-distutils

python3.12 コマンドで起動できるようになります。

pip と仮想環境の準備
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.12
python3.12 -m venv ~/envs/linux-dev
source ~/envs/linux-dev/bin/activate

2. プロジェクトをクローン／マウント
Windows 上のソースコードディレクトリ
たとえば D:\city_chain_project\DAGs\libs\algorithm\ 配下にあるなら、WSL 側からは
/mnt/d/city_chain_project/DAGs/libs/algorithm/ でアクセスできます。
下記のようになればOK
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_ack$



CLI
単一 ACK の同期検証
poh-ack verify --input /path/to/ack.json --ttl 300

単一 ACK の非同期検証
poh-ack verify-async --input /path/to/ack.json --ttl 300


開発 / テスト
# dev 環境構築
pip install maturin click pydantic ed25519 base58 pytest pytest-asyncio

# Rust 版ビルド & Python テスト
maturin develop --release
pytest -q

