poh_network/                              ← リポジトリルート
├── LICENSE                              ← ライセンス (Apache-2.0 等)
├── README.md                            ← パッケージ概要・インストール手順・使い方
├── .gitignore                           ← __pycache__/、*.py[cod] など
├── pyproject.toml                       ← PEP 517/518 ビルド設定（依存関係、パッケージ名、バージョン等）
└── poh_network/                         ← 実際の Python モジュール
    ├── __init__.py                      ← パッケージ定義（バージョン読み込みなど）
    ├── app_network.py                   ←　エンドポイント
    ├── network.py                       ← 高レベル API （broadcast, subscribe, gather）
    ├── peer_manager.py                  ← ピア管理（登録・疎通チェック・リスト取得）
    ├── grpc_server.py                   ← gRPC(AIO) サーバ：PoH Tx ブロードキャスト受信
    ├── http_server.py                   ← HTTP(AioHTTP) サーバ：/broadcast エンドポイント
    ├── udp_listener.py                  ← UDP 受信リスナー：DatagramProtocol 実装
    ├── protocols/                       ← Protobuf 定義・生成コード格納
    │   ├── poh.proto                    ← PoH Tx メッセージ定義
    │   └── poh_pb2_grpc.py              ← `protoc --python_out=.` で生成されたコード
    └── tests/                           ← 単体テスト
        ├── __init__.py
        ├── test_network.py              ← `network.py` の統合的テスト
        ├── test_peer_manager.py         ← ピア管理ロジックのテスト
        ├── test_grpc_server.py          ← gRPC サーバのメッセージ受信テスト
        ├── test_http_server.py          ← HTTP エンドポイントテスト
        └── test_udp_listener.py         ← UDP リスナーのデータ受信テスト

poh_network は PoH（Proof of History）トランザクションをネットワーク越しにブロードキャスト／受信・管理するためのライブラリです。大きく分けると以下の５つの機能を持ちます。

1. ピア管理（PeerManager）
役割
ブロードキャスト先のノード（ピア）一覧を管理します。
プロトコル（gRPC／HTTP／UDP）ごとに複数アドレスを登録・削除・取得可能。

主なメソッド
add_peer(protocol: str, address: str)
remove_peer(protocol: str, address: str)
get_peers(protocol: str) -> list[str]

永続化
CLI の add-peer／remove-peer で操作すると、ユーザーのホームディレクトリに ~/.poh_peers.json を書き換えます。

2. ネットワークマネージャ（NetworkManager）
役割
登録済みのピアに対して、PoH Tx をまとめて一斉送信（fan-out）します。
非同期に gRPC／HTTP／UDP の３方式で同時並行にリクエストを投げ、成功／失敗の結果を集約。

主なメソッド
async broadcast(tx: Tx) -> tuple[bool, bool, bool]
返り値は (grpc_ok, http_ok, udp_ok)。
内部で asyncio.gather() を使って並列実行し、タイムアウトや個別エラーをハンドリング。

3. gRPC サーバ（grpc_server.py）
役割
PohService.Broadcast(Tx)→Ack の gRPC を受け付け、受信した Tx をローカルストレージ（poh_storage）に保存。
Python の grpc.aio.Server を使った完全非同期実装。

主な処理フロー
.Broadcast コール受信
StorageManager を作成→save_tx(tx)
成功なら Ack(success=True)、例外なら Ack(success=False) を返却
サーバの起動／終了は serve(port, base, db) 関数でラップ

4. HTTP サーバ（http_server.py）
役割
aiohttp を使った RESTful API で同じく Tx ブロードキャスト受信を実現。

エンドポイント例：
POST /v1/tx → JSON ボディ（tx_id, holder_id, timestamp, payload_b64）を受け取り保存 → JSON でステータス返却

特徴
ミドルウェア的に StorageManager をアプリケーションインスタンスに紐付け。
デフォルトキー警告を回避しつつ、きちんと app["storage"] からアクセス。

5. UDP リスナ（udp_listener.py）
役割
asyncio.DatagramProtocol をラップして UDP パケットを受信。
受信データを base64→バイト列に戻し、StorageManager.save_tx で永続化。
単方向・軽量ブロードキャスト向け。

主な処理フロー
ソケットバインド（listen_udp(port, base, db)）
受信コールバックで on_datagram_received(data, addr)
JSON 解釈→Tx オブジェクト生成→保存

6. CLI（app_network.py）
役割
端末からの操作をひとまとめにしたエントリポイント。

サブコマンド例：
add-peer / remove-peer / list-peers
broadcast（単発 Tx の送信）
serve-grpc / serve-http / listen-udp

特徴
argparse で柔軟に引数パース
単一の async def main() に集約
Windows でも動くように WindowsSelectorEventLoopPolicy を設定
Ctrl-C 捕捉 → 全タスク優雅終了

全体の非同期設計
各サーバ／クライアント共に asyncio （async def＋await）ベース。
I/O（ネットワーク／ファイル／SQLite）はすべて非同期ドライバ（grpc.aio, aiohttp, aiofiles, aiosqlite）を利用。
タスクの並列実行に asyncio.create_task や asyncio.gather を活用。

以上が poh_network の主要コンポーネントと、その機能・役割の詳細解説です。これらを組み合わせることで、PoH トランザクションを多様なプロトコル経由で送受信し、ネットワーク全体に拡散／集約することができます。



#　プロトコル定義から Python コードを再生成する手順
（grpc-tools を使った“本番運用向け”のベストプラクティス）

1. 依存パッケージのインストール
まず一度だけ、開発環境に gRPC コンパイラ（protoc）本体 と
Python プラグイン grpcio-tools を入れます。
# 仮想環境を想定
pip install --upgrade pip
pip install grpcio grpcio-tools
※ Linux では protoc が同梱されるので追加パッケージ不要。
Homebrew 等で独自の protoc を入れていても OK ですが
バージョンをそろえる ことを推奨します（例: 3.22+）。

2. ディレクトリ構成を確認
poh_network/
└── poh_network/
    └── protocols/
        └── poh.proto
生成物 poh_pb2.py と poh_pb2_grpc.py も 同じ protocols/ フォルダ に出力すると import が楽です。

3. protoc 実行コマンド
プロジェクトルート（pyproject.toml がある階層）で：
python -m grpc_tools.protoc -I poh_network\protocols ^
 --python_out=poh_network\protocols ^
 --grpc_python_out=poh_network\protocols ^
 poh_network\protocols\poh.proto

--python_out=… : メッセージクラス (poh_pb2.py) を生成
--grpc_python_out=…: サービススタブ/サーバ (poh_pb2_grpc.py) を生成

実行後:
poh_network/protocols/
├── poh.proto
├── poh_pb2.py        ← 生成
└── poh_pb2_grpc.py   ← 生成

4. 生成ファイルを Git に入れる？入れない？
運用方針	メリット	デメリット・注意点
入れる（推奨）	• インストール先で protoc 不要	• 定義を変えたら 忘れず再生成
入れない	• リポジトリが少し軽い	• ビルド時に自動生成タスクを用意する

Python パッケージとして配布するなら「入れる」一択です。
パッケージ利用者に grpcio-tools を強制しないで済みます。

6. 「ビルド時に自動生成」したい場合
setuptools の setup.py hook 例
# setup.py
from setuptools import setup
from setuptools.command.build_py import build_py
import subprocess, pathlib

PROTO_PATH = pathlib.Path("poh_network/protocols/poh.proto")

class BuildWithProto(build_py):
    def run(self):
        # 生成済みならスキップしても可
        subprocess.check_call([
            "python", "-m", "grpc_tools.protoc",
            "-I", str(PROTO_PATH.parent),
            "--python_out", str(PROTO_PATH.parent),
            "--grpc_python_out", str(PROTO_PATH.parent),
            str(PROTO_PATH),
        ])
        super().run()

setup(
    cmdclass={"build_py": BuildWithProto},
    # 以降は通常の setup(...) 引数
)

pyproject.toml + PEP-517 でも同様に
build-backend をカスタムするか、scikit-build-core などでフック可能です。

7. 定義を変更したときのチェックリスト
poh.proto を書き換える
make proto で再生成
生成物を 必ず git add
ライブラリ側 (poh_network.grpc_server, クライアントコード) で
新フィールドに合わせてロジックを更新
pytest で全テストグリーンを確認
バージョンを上げてリリース (0.1.x → 0.2.0 など)

これで 「本番運用では必ず再生成」 の要件を無理なく守れます。
いつでも make proto さえ実行すれば最新状態になりますので、
CI（GitHub Actions など）でも “定義変更を検知 → 再生成 → テスト” を組み込んでおくと安心です。


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

/ 4.24.4 ソースを C 拡張スキップ でビルド
pip uninstall -y protobuf
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
pip install protobuf==5.27.0
REM ↑ 変数のおかげでランタイムでは純 Python 実装のみロードされる
手元で wheel をビルドしないので Visual C++ エラーは出ない

pytest 用単体テスト。
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_ttl\pytest poh_network/tests

何が引っ掛かっているか？
現象	原因
Windows fatal exception: access violation	Protobuf 4.25 系 C 拡張 (_upb) が Python 3.12 + Windows と ABI 食い違いを起こし、インポート直後にクラッシュ
pip install --no-binary=protobuf protobuf==4.24.4 が大量の C エラーで失敗	--no-binary は “wheel を落とさずソースから” という意味だが、 ソース版 4.24.4 には C 拡張のビルドが必須 → Visual C++ で大量エラー

いま何をしようとしているか？
WSL（Ubuntu）上に Python3.12 環境を作り、
VSCode Remote-WSL でコードを開き、
プロジェクトルートをマウント して editable install → pytest
Windows ⇔ WSL 間でファイルもネットワークも透過的に共有
…この流れであれば、Windows 固有の Protobuf ABI 問題に悩まされず、他クレートとの相互通信もスムーズに行えます。ぜひお試しください！

1. WSL のセットアップ
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

=================================================== warnings summary ===================================================
poh_network/tests/test_http_server.py::test_http_broadcast
  /mnt/d/city_chain_project/DAGs/libs/algorithm/poh_network/poh_network/http_server.py:28: NotAppKeyWarning: It is recommended to use web.AppKey instances for keys.
  https://docs.aiohttp.org/en/stable/web_advanced.html#application-s-config
    app["storage"] = storage

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============================================= 5 passed, 1 warning in 2.02s =============================================


Linux 上では Protobuf の manylinux wheel が正しく読み込まれ、AV は発生しません。
grpcio、grpcio-tools、aiohttp などもネイティブに動きます。

4. Windows ⇔ WSL 間の相互通信
ファイル I/O
Windows 側からソースを編集し、WSL 側の Python に即反映されます（逆も同様）。VSCode Remote-WSL を使えばエディタは Linux 環境を直接叩きます。

ネットワーク
WSL の localhost:<port> は Windows からも localhost:<port> でアクセス可能です。
例えば WSL 上で
poh-network serve-grpc --port 50051 --base ... --db ...
と起動すると、Windows 側の別プロセス（PowerShell や別の WSL ターミナル）から
grpc.aio.insecure_channel("localhost:50051") で繋げます。


# 10-3 test_network.py はモックです！
統合テストはここでは大変すぎるので、モックでいったん回避！
import asyncio
import pytest
from poh_network.network import NetworkManager
from poh_network.peer_manager import PeerManager
from poh_storage.types import Tx

@pytest.mark.asyncio
async def test_broadcast_monkeypatch(monkeypatch):
    peers = PeerManager()
    peers.add_peer("grpc", "dummy:1")
    peers.add_peer("http", "dummy:2")
    peers.add_peer("udp",  "dummy:3")

    nm = NetworkManager(peers)
    tx = Tx(tx_id="1", holder_id="h", timestamp=0.0, payload=b"p")

    # 各内部送信関数を即成功するフェイクに差し替え
    monkeypatch.setattr(nm, "_broadcast_grpc", lambda _tx: asyncio.sleep(0, True))
    monkeypatch.setattr(nm, "_broadcast_http", lambda _tx: asyncio.sleep(0, True))
    monkeypatch.setattr(nm, "_broadcast_udp",  lambda _tx: asyncio.sleep(0, True))

    results = await nm.broadcast(tx)
    assert results == [True, True, True]

本格的に gRPC/HTTP/UDP を立てて I/O する結合テストは CI コストが高い
 ⇒ ここでは内部メソッドをモンキーパッチしてロジックのみ検証


# ❺ まとめ - “混乱しない” 運用指針
venv は OS 単位で 1 個ずつ（win-dev, linux-dev など分かりやすい名前）。
wheel は CI で量産 → 共有 wheelhouse に置く。
開発者は
# Windows
py -m venv .venv && .venv\Scripts\activate
pip install --find-links \\share\wheelhouse\windows -r requirements.txt

# WSL
python3 -m venv .venv && source .venv/bin/activate
pip install --find-links /mnt/share/wheelhouse/linux -r requirements.txt
だけで済むようにする。

これで 「500 crate × 2 OS 手動ビルド」地獄 から解放されます。