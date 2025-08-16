※　Windows側がC拡張処理できず未build

poh_request (1) – PoH_REQ JSON
poh_request/                                 ← ① Git リポジトリのルート
├── LICENSE                                  ← OSS ライセンス (Apache‑2.0 推奨)
├── README.md                                ← パッケージ概要 / Quick‑Start / 仕様
├── CHANGELOG.md                             ← バージョン履歴 (Keep a Changelog)
├── .gitignore                               ← __pycache__/ などビルド生成物を除外
├── .editorconfig                            ← コードフォーマット統一設定
├── .pre-commit-config.yaml                  ← black/ruff/mypy など自動フォーマッタ
├── pyproject.toml                           ← PEP 621 準拠ビルド設定 & 依存一覧
├── .github/workflows                        ← CI 用スクリプトや Github‑Actions ワークフロー
│   └── ci.yml                               ← GitHub Actions (テスト & lint & build)
└── poh_request/                             ← ② 実際の Python パッケージ
    ├── __init__.py                          ← ルート名前空間・バージョン定義
    ├── config.py                            ← 接続先 RPC エンドポイント等の設定
    ├── exceptions.py                        ← 独自例外 (PoHRequestError / EncodeError…)
    ├── schema.py                            ← Pydantic V2 による PoH_REQ JSON スキーマ
    ├── builder.py                           ← Tx 組み立てロジック (PoHRequestBuilder)
    ├── sender.py                            ← 送信ラッパ (sync+async 両対応 HTTP/RPC)
    ├── cli.py                               ← `poh-request` CLI エントリーポイント
    ├── utils.py                             ← 再利用ユーティリティ（署名・Base58 等）
    └── tests/                               ← ③ 単体 & 結合テスト群
        ├── __init__.py
        ├── conftest.py                      ← pytest 用フィクスチャ (モック RPC など)
        ├── test_schema.py                   ← JSON スキーマ検証テスト
        ├── test_builder.py                  ← PoHRequestBuilder の正常系 / 異常系
        ├── test_sender.py                   ← 送信モックで retry・タイムアウトを検証
        └── test_cli.py                      ← CLI コマンドエンドツーエンド

流れ
PoHRequestBuilder が PoHRequest インスタンスを生成
ビルダーが Ed25519 署名（libsodium/NaCl）を付与
署名済 JSON → Base58 エンコード → ペイロード文字列完成
AsyncSender が HTTP POST（config.settings.rpc_endpoint）で送信
サーバー JSON を PoHResponse として返す
CLI では build / send / decode サブコマンドで上記を呼び出し

2. モジュール別詳細
■ schema.py
| モデル        | 主フィールド                                　　　　                | バリデーション                                         |
| ------------- | ---------------------------------------------------------------- | ----------------------------------------------- |
| `PoHRequest`  | `token_id, holder_id, amount, nonce, created_at, signature`      | - `amount >=1`<br>- `created_at` 無タイムゾーン→UTC 付与 |
| `PoHResponse` | `txid, status("accepted/queued/rejected"), received_at, reason?` | `Literal` でステータス限定                              |

tip: extra="allow" にしているのでテスト内の monkey‑patch で model_dump_json を上書き可。

■ utils.py
| 関数                                              | 説明                                   |
| ------------------------------------------------- | ------------------------------------ |
| `generate_nonce()`                                | 64bit 乱数 (`secrets.randbits(63)`)    |
| `b58encode / b58decode`                           | `base58.b58encode`/`b58decode` の薄ラッパ |
| `async_backoff_retry(coro, attempts, base_delay)` | 等比 back‑off（1,2,4…）で再試行              |


■ builder.py
| メソッド                        | 役目                                                 |
| ------------------------------ | -------------------------------------------------- |
| `__init__`                     | `PoHRequest` を内部生成（nonce自動, created\_at=UTC now）   |
| `_canonical_json(exclude_sig)` | **空白ゼロ**の JSON bytes（`separators=(",", ":")`）      |
| `_digest()`                    | `SHA‑256(canonical_json_without_signature)`        |
| `sign()`                       | `self._sk.sign(digest).signature → Base58` をモデルへ保存 |
| `encode()`                     | 署名が無ければ sign → 署名込 JSON を Base58 返却                |


※ 署名対象は「signature フィールドを除いた JSON」。テスト側でも同じロジックでベリファイ。

■ sender.py
コンストラクタで timeout, attempts を config.settings から取得
_once() 内で httpx.AsyncClient.post
HTTP status≧400 や JSON validation 失敗で SendError
上位の async_backoff_retry でリトライ
send_sync(payload_b58)
asyncio.run( AsyncSender().send(...) ) – 同期ラッパ

■ config.py
class Settings(BaseSettings):
    rpc_endpoint   = Field(..., alias="POH_RPC_ENDPOINT")
    request_timeout= Field(10.0, alias="POH_REQUEST_TIMEOUT")
    retry_attempts = Field(3,    alias="POH_RETRY_ATTEMPTS")
    backoff_base   = Field(0.5,  alias="POH_BACKOFF_BASE")
.env も読み込む。ファイル先読み＆シングルトン settings を 全モジュール共通で利用。

■ cli.py (poh-request)
| コマンド  | 主要オプション                                           | 動作                          |
| -------- | ------------------------------------------------------- | --------------------------- |
| `build`  | `--token-id --holder-id --amount --key --nonce? --out?` | Builder で署名 → Base58 を出力/保存 |
| `send`   | `[payload_file]`                                        | Base58 を読み込んで **同期送信**      |
| `decode` | `<payload_b58>`                                         | Base58 をデコード→整形 JSON        |


typer が自動で poh-request --help を生成。

3. テスト
pytest / pytest‑asyncio strict
ハッピー＋エラー系の両方を網羅
monkeypatch でモジュール関数を差し替え、外部 I/O を疑似化

例：httpx.AsyncClient をモック transport に置換
confetest.py で 単一イベントループを共有（Windows 上は SelectorLoop）

4. ビルド & 配布
pyproject.toml – setuptools.build_meta でビルド
ライセンス周りは Deprecation Warning が出るので後で SPDX 表記へ
python -m build で sdist / wheel 作成可
CI（GitHub Actions）では Linux/Windows の Python 3.12 で pytest, ruff, mypy を実行

5. 既知のハマりどころ
症状	原因/対策
Windows で “access violation”	PyNaCl 1.5.0 + libsodium DLL の衝突
→ ① PyNaCl 1.4.0 に固定 ② 正しいアーキの DLL を PATH 先頭に ③ EDR/AV の干渉除去
Test 失敗: TypeError: datetime not JSON serializable	builder の canonical_json 漏れ → 修正済
Build 時に setuptools の license 警告	project.license = "Apache-2.0" へ変更予定

まとめ
poh_request は
Pydantic v2 モデル＋nacl 署名
シンプルな Builder / Sender パターン
非同期実行＆CLI も装備
テスト＋CI が揃っているので、RPC エンドポイントを差し替えればすぐ運用に乗せられる


#　wheel を dist\ に置きたいなら
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

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
sudo apt install -y protobuf-compiler
sudo apt install python3.12-dev

これでシステムに
/usr/lib/x86_64-linux-gnu/libpython3.12.so
/usr/include/python3.12/…
といったファイルが入ります。
python3.12 コマンドで起動できるようになります。

# pip と仮想環境の準備
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.12
python3.12 -m venv ~/envs/linux-dev
source ~/envs/linux-dev/bin/activate

2. プロジェクトをクローン／マウント
Windows 上のソースコードディレクトリ
たとえば D:\city_chain_project\DAGs\libs\algorithm\ 配下にあるなら、WSL 側からは
/mnt/d/city_chain_project/DAGs/libs/algorithm/ でアクセスできます。
下記のようになればOK
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_request

2. Cargo に「Python をリンクしてね」と教えてあげる
② PyO3 に正しい Python を教える
もし python3.12 を明示したい場合：
export PYTHON_SYS_EXECUTABLE=$(which python3.12)

# 依存を入れる
pip install "motor[asyncio]"

editable インストールを更新
プロジェクト直下 ( pyproject.toml があるディレクトリ ) で
pip install -e .

各クレート（poh_storage/、poh_ttl/、poh_network/）それぞれで editable インストール：
# 例: poh_storage
cd poh_storage
　※プロジェクトの test extras をまとめて拾ってくる
pip install -e '.[test]'
python -m pytest poh_storage/tests

# 同様に poh_ttl
cd ../poh_ttl
pip install -e '.[test]'
python -m pytest poh_ttl/tests

# 同様に poh_types
cd ../poh_types
pip install -e '.[test]'
python -m pytest poh_types/tests

# そして poh_request
cd ../poh_request
pip install -e '.[test]'
#　wheel を dist\ に置きたいなら comandプロンプトから（ややこしいね。。）
pip install -e .

python -m pip install --upgrade build   # 必須
python -m pip install --upgrade twine  # PyPI に上げるなら
python -m build             # ← wheel と sdist の両方を生成

======================================================== test session starts ========================================================
platform linux -- Python 3.12.3, pytest-8.4.1, pluggy-1.6.0
rootdir: /mnt/d/city_chain_project/DAGs/libs/algorithm/poh_request
configfile: pyproject.toml
plugins: anyio-4.9.0, cov-6.2.1, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 16 items

poh_request/tests/test_builder.py ..                                                                                          [ 12%]
poh_request/tests/test_cli.py ...                                                                                             [ 31%]
poh_request/tests/test_schema.py ....                                                                                         [ 56%]
poh_request/tests/test_sender.py ...                                                                                          [ 75%]
poh_request/tests/test_utils.py ....                                                                                          [100%]

======================================================== 16 passed in 1.02s =========================================================


# Windows側でテストをパスさせる方法
.dllがないとクラッシュする。そのため、.dllをコピーして入れる。
でも、やっぱり動かないので、諦めて後回しにしている

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_request>curl -L -o libsodium-win64.zip https://download.libsodium.org/libsodium/releases/libsodium-1.0.19-msvc.zip
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 18.8M  100 18.8M    0     0  1474k      0  0:00:13  0:00:13 --:--:-- 3381k

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_request>tar -xf libsodium-win64.zip

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_request>copy /Y libsodium-win64\bin\libsodium-23.dll "%VIRTUAL_ENV%\Scripts\libsodium.dll"
libsodium-win64\bin\libsodium-23.dll
存在しないデバイスを指定しました。
        0 個のファイルをコピーしました。

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_request>