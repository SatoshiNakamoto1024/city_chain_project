poh_config/                                ← リポジトリルート
├── LICENSE                                ← ライセンス (Apache-2.0 など)
├── README.md                              ← パッケージ概要／インストール手順／使い方
├── .gitignore                             ← __pycache__/、*.py[cod]、dist/ など
├── pyproject.toml                         ← ビルド設定／依存関係／プロジェクトメタデータ
└── poh_config/                            ← 実際の Python モジュール
    ├── __init__.py                        ← バージョン定義など
    ├── app_config.py                      ←　エンドポイント
    ├── config.py                          ← `ConfigManager` クラス：ファイル読み込み＆キャッシュ管理
    ├── types.py                           ← 設定項目の型定義 (`MIN_POH_REQUIRED: int` 等)
    ├── parsers/                           ← 各フォーマットのパーサ群
    │   ├── __init__.py
    │   ├── toml_parser.py                 ← TOML → dict
    │   ├── json_parser.py                 ← JSON → dict
    │   └── yaml_parser.py                 ← YAML → dict
    ├── watchers.py                        ← `asyncio` ベースのファイル監視＆自動リロード
    └── tests/                             ← 単体テスト
        ├── __init__.py
        ├── test_toml_parser.py            ← TOML パーサの動作テスト
        ├── test_json_parser.py            ← JSON パーサの動作テスト
        ├── test_yaml_parser.py            ← YAML パーサの動作テスト
        ├── test_config_manager.py         ← `ConfigManager` の同期／非同期ロードテスト
        └── test_watchers.py               ← ファイル変更時のリロード動作テスト

poh_config は、TOML/JSON/YAML フォーマットの設定ファイルを非同期に読み込み・管理し、さらにファイル変更を検知してリアルタイムに設定をリロードできるユーティリティ群です。主な機能をコンポーネント別にまとめると以下のとおりです。

1. 設定読み込み・キャッシュ管理 (ConfigManager)
非同期ロード (load())
aiofiles を使ってファイルをノンブロッキングに読み込み
拡張子に応じたパーサ（TOML/JSON/YAML）を呼び出し、Python の dict に変換
内部キャッシュ (self._data) に保持し、次回以降の即時参照を可能に

同期ロード (load_sync())
まずキャッシュを返し、未ロード時は同期的にファイルを読み込んでパース
asyncio イベントループをブロックせず使えるよう設計
キャッシュ取得 (get(key, default))
一度ロードされた設定からキーを取り出す。未ロード時はエラーを投げることで “必ず先に load() してください” と明示

2. フォーマット別パーサ（parsers/）
TOML パーサ (toml_parser.py)
tomli（または toml）を利用して文字列→ dict
非同期版はファイルパスを渡し、同期版はテキストを渡せるように parse() と parse_text() を両対応

JSON パーサ (json_parser.py)
組み込み json モジュールによる即時パース
非同期／同期とも同じロジックをシンプルに実装

YAML パーサ (yaml_parser.py)
ruamel.yaml または PyYAML を用い、設定ファイル → dict
こちらも非同期／同期を両対応

3. ファイル監視＆自動リロード (watchers.py)
汎用的なファイルウォッチャ (watch_file)
watchfiles.awatch で指定ディレクトリを監視
初回読み込み後に必ずコールバックを実行
デバウンス機能：連続するファイル変更をまとめて一度だけ通知
キャンセル可能な asyncio.Task として起動し、task.cancel() で止められる

ConfigManager.watch() メソッド
設定専用に最適化したラッパー
変更通知を受けるたび新しい設定をロードし、コールバックに渡す

4. 型安全な設定オブジェクト (types.py)
@dataclass ベースの Config
必須設定項目（例：MIN_POH_REQUIRED: int, TTL_SECONDS: float）を型注釈付きで定義
Config.from_dict() で単純な dict → Config インスタンスへ変換
「設定として存在すべき項目」をクラスレベルで固定し、タイプチェックとドキュメント性を両立

5. CLI エントリポイント (app_config.py)
poh-config load <path>
初回ロードして JSON で標準出力
パイプ／リダイレクトして他ツールと組み合わせ可能
poh-config watch <path> [--debounce]
初回ロード → JSON 出力
以後ファイル変更を監視して、その都度最新設定を JSON 出力
Ctrl-C/TERM ハンドリング済みで安全に停止

全体の利用イメージ
起動時
mgr = ConfigManager(Path("config.toml"))
data = await mgr.load()            # 非同期読み込み＋キャッシュ
value = mgr.get("MIN_POH_REQUIRED") # キャッシュから即時取り出し

動作中に設定を反映
async def on_reload(new_cfg):
    # new_cfg は dict; 必要なら Config.from_dict で型変換
    update_runtime_settings(new_cfg)
task = asyncio.create_task(watch_file(cfg_path, on_reload))

# 変更を検知 → on_reload が呼ばれる
CLI から手軽にファイルを一度だけロードして中身を確認
$ poh-config load config.yaml

# 運用中に設定変更をリアルタイム確認
$ poh-config watch config.yaml --debounce 0.2
以上が poh_config の全機能です。

非同期対応 で I/O をブロックせず、
フォーマット自動判別＋同期／非同期両ロード、
型安全な Dataclass、
CLI & ファイルウォッチャ、
を一式提供し、設定周りのコードをシンプルかつ堅牢に保ちます。


#　dilithium5 を埋め込んだので、python312でのサーバー起動は下記から
# まずはpython312に各種インストール
作業	具体例
3.12のPython.exeを確認	（なければインストール）
D:\Python\Python312\python.exe -m venv D:\city_chain_project\.venv312
作ったあと、
D:\city_chain_project\.venv312\Scripts\activate.bat
という具合に、仮想にはいること。

D:\Python\Python312\python.exe -m pip install flask flask-cors requests boto3 qrcode pytest PyJWT cryptography pillow qrcode[pil]

これにより、Python 3.12 環境でテストが実行され、既にインストール済みの Pillow（PIL）が利用されるはずです。

#　wheel を dist\ に置きたいなら
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

pytest 用単体テスト。
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_config\pytest poh_config/tests

================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0
rootdir: D:\city_chain_project\DAGs\libs\algorithm\poh_config
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 5 items

poh_config\tests\test_config_manager.py .                                                                        [ 20%]
poh_config\tests\test_json_parser.py .                                                                           [ 40%]
poh_config\tests\test_toml_parser.py .                                                                           [ 60%]
poh_config\tests\test_watchers.py .                                                                              [ 80%]
poh_config\tests\test_yaml_parser.py .                                                                           [100%]

================================================== 5 passed in 0.96s ==================================================


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
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_network$

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

# そして poh_network
cd ../poh_network
pip install -e '.[test]'
#　wheel を dist\ に置きたいなら comandプロンプトから（ややこしいね。。）
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

#　テストはWSL から
python -m pytest poh_network/tests
