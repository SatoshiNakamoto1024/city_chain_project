---
layout: default
title: データフロー
---

# フェデレーションモデルの詳細設計

## データフロー

![データフローチャート](./data_flow.png)

## 各ステップの詳細説明

### 1. 送信用index.htmlからトランザクションデータ受信
ユーザーが送信用フォームからトランザクションデータを送信します。このデータには市町村（municipality）と大陸（continent）の情報が含まれます。

### 2. app.pyでデータ処理
送信されたトランザクションデータをapp.pyが受信し、`municipality`と`continent`を抜き出します。

### 3. 大陸の選択
抜き出した`continent`情報に基づいて、該当する大陸のチェーン（municipal_chain）を選択します。

### 4. municipal_chainでの処理
選択された大陸の市町村チェーンでトランザクションを処理し、`send_pending`に保存します。

### 5. ブロック生成と承認
`send_pending`に保存されたトランザクションが一定数（例：500件）に達すると、ブロックが生成され、承認されます。

### 6. continental_main_chainへの転送
承認されたブロックはcontinental_main_chainに転送され、保留リストに保存されます。

### 7. 受信側のプロセス
ユーザーが受信用フォームから信号を送信し、app.pyが信号を処理します。continental_main_chain経由で保留リストにアクセスし、10大陸に共有されます。

### 8. municipal_chainでの受信トランザクション処理
該当するmunicipal_chainで受信トランザクションを処理し、`receive_pending`に保存します。ブロックが生成・承認されると`complete`に更新され、MongoDBに保存されます。

### 9. 後続処理
保存されたデータは分析用データベースへの移行、Gossipアルゴリズムによる他の市町村とのデータ共有、他のDAppsからのデータ抽出などに利用されます。

### 10. 全体像
ブロックチェーンのプログラムで、ログインからDApps、main_chain、gossipまでの流れを考慮し、データベースのデータやフォルダ構造を整理する設計方法を以下に示します。

1. データフローを考える
データの流れが「ログイン ⇒ DApps ⇒ main_chain ⇒ gossip」である場合、それぞれの段階に対応するデータを整理して保存する必要があります。

主要データカテゴリ
ログイン情報
ユーザー情報、認証データ、ログイン履歴。
DAppsトランザクション
ユーザーのアクション（送金、リクエスト）やステータス。
メインチェーンのデータ
承認されたトランザクション、ブロック情報。
ゴシッププロトコル関連データ
ネットワーク内で共有されるトランザクションやブロック情報のメタデータ。
2. ディレクトリ設計
データディレクトリの例
以下のようにフォルダを分けて保存する方法が有効です：

project_root/
├── data/                  # 全データを保存
│   ├── login/             # ログイン関連データ
│   │   ├── users.json     # ユーザー情報（ハッシュ化されたパスワード含む）
│   │   ├── logs/          # ログイン履歴
│   │       ├── 2025-01-25.log
│   │       ├── 2025-01-26.log
│   ├── dapps/             # DApps側で生成されたデータ
│   │   ├── pending/       # 未承認のトランザクション
│   │   │   ├── tx_001.json
│   │   │   ├── tx_002.json
│   │   ├── completed/     # 承認済みトランザクション
│   │       ├── tx_003.json
│   │       ├── tx_004.json
│   ├── main_chain/        # メインチェーンのデータ
│   │   ├── blocks/        # ブロック情報
│   │       ├── block_001.json
│   │       ├── block_002.json
│   │   ├── state/         # チェーンの現在の状態
│   │       ├── state.json
│   ├── gossip/            # ゴシッププロトコル関連データ
│       ├── messages/      # ネットワーク内で共有されるメッセージ
│       │   ├── msg_001.json
│       │   ├── msg_002.json
│       ├── peers/         # ピア情報
│           ├── peer_001.json
│           ├── peer_002.json
3. MongoDBでの設計
上記のフォルダ構造をMongoDBで管理する場合、コレクションとデータ構造を以下のように設計します。なお、
　・データディレクトリ (dbPath で指定する場所):は、ローカルにMongoDBがデータを物理的に保存するディレクトリです。MongoDBサーバー（mongodプロセス）が動作しているマシン上に存在します。
　・ポート番号（例: 27017）: アプリケーション（DAppsなど）は、ネットワーク経由でこのポートを使ってMongoDBサーバーに接続します。しかし、実際のデータはMongoDBが動作しているマシンのディスク上（dbPathで指定したディレクトリ内）に保存されます。直接アクセスはできませんし、覗きに行ってもファイルが壊れるので閲覧は出来ない仕組みです。

# Rust と Python のデータ型の対応関係
BSON は型情報を保持するため、言語間でデータ型が一致していれば問題ありません。ただし、以下の点に注意してください：

BSON 型	 Python	         Rust
String	str または str	 String
Int32	 int	         i32
Int64	 int	         i64
Double	 float	         f64
ObjectId bson.ObjectId	 bson::oid::ObjectId
Boolean	 bool	         bool
Array	 list	         Vec<T>
Document dict	         bson::Document
上記のようにPython と Rust の BSON サポートは豊富であるため、基本的なデータ型のマッピングは問題なく行われます。

#　データベース設計
Database: blockchain_system
Collection: login
Fields:
_id: 自動生成ID
username: ユーザー名（ユニーク）
password_hash: パスワードのハッシュ
last_login: 最終ログイン日時

Collection: dapps_transactions
Fields:
_id: 自動生成ID
status: pending または completed
sender: 送信者
receiver: 受信者
amount: トークン量
timestamp: 作成日時

Collection: main_chain_blocks
Fields:
_id: 自動生成ID
block_number: ブロック番号
transactions: トランザクションの配列
previous_hash: 前のブロックのハッシュ
timestamp: 作成日時

Collection: gossip_messages
Fields:
_id: 自動生成ID
message_id: メッセージID
content: メッセージ内容
sender: 送信者ピア
timestamp: 作成日時

4. 実装方針
データ保存:
MongoDBに保存すると同時に、重要なデータはローカルディスク（例：data/ディレクトリ）にバックアップとして保存。
保存形式はJSON。

モジュール分割:
pymongodb.py: MongoDB操作（CRUD）をモジュール化。
app_dapps.py: DApps側のデータ操作コード。
app_main_chain.py: メインチェーンのデータ操作コード。
app_gossip.py: ゴシッププロトコル関連コード。
フォルダ設計を反映:

pymongodb.pyにdbPathを設定し、フォルダ構造に基づいたCRUDを作成。
5. 実装例
MongoDB接続（pymongodb.py）
import os
import pymongo

class MongoDBHandler:
    def __init__(self, db_name="blockchain_system", host="localhost", port=27017):
        self.client = pymongo.MongoClient(host, port)
        self.db = self.client[db_name]

    def insert_data(self, collection, data):
        return self.db[collection].insert_one(data)

    def find_data(self, collection, query):
        return list(self.db[collection].find(query))

    def update_data(self, collection, query, update):
        return self.db[collection].update_one(query, {"$set": update})

    def delete_data(self, collection, query):
        return self.db[collection].delete_one(query)
結論
フォルダ構造とデータベース設計を統一して管理すると、DAppsとメインチェーン間のデータの流れが明確になり、拡張性も高くなります。MongoDBは、CRUD操作をモジュール化して再利用可能に設計することで、効率的に管理できます。

# grpcipのインストール
wsl --install
sudo apt update
sudo apt install python3 python3-pip -y

2．WSL 上で grpcio をインストール
python3 -m venv venv
source venv/bin/activate
pip install grpcio grpcio-tools

3．Ubuntu のパッケージを最新化
sudo apt update && sudo apt upgrade -y
  ID:satoshi
  PW:greg1024

Python と venv をインストール
sudo apt install python3 python3-pip python3-venv -y

仮想環境を作成
・Cドライブに venv を作る
・WSL のローカルディレクトリ (~) に新しい仮想環境を作る。
　以下で、"C:\Users\kibiy\venvs\example_grpc"というフォルダーが作られる。
  これが重要！D:にvenvを作ってもエラーになるよ！
mkdir -p ~/venvs/example_grpc
python3 -m venv ~/venvs/example_grpc

grpcio をインストール
pip install --no-cache-dir grpcio grpcio-tools

Windows 側の D:\city_chain_project\network\DB\immudb\py_immu を WSL で開く
cd /mnt/d/city_chain_project/network/DB/immudb/py_immu

Python インタープリターを開く
python3

gRPC が正しくインストールされているか確認
import grpc
print(grpc.__version__)

・1.70.0　などと表示されればOK

Python インタプリタを終了
exit()

① WSLの venv の現在地
今、venv は WSL の home/satoshi/venvs/example_grpc/（つまり C: 内） にあります。
WSL の home フォルダは、Windows の C:\Users\kibiy\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu_*\ 以下にありますが、直接 Windows からアクセスするのは推奨されません。
そのため、Windows から見るときは、エクスプローラーで以下のアドレスを入力：
\\wsl$\Ubuntu\home\kibiy\venvs\example_grpc\
で開けます。

venv の状態を確認する
まず、以下のコマンドで venv が正しく作成されているか確認しましょう。
ls -l ~/venvs/example_grpc/

正常なら、以下のようなフォルダが見えるはずです。
bin  include  lib  lib64  pyvenv.cfg

② WSL から D: のコードを読み込む
今やりたいことは WSL から D:\city_chain_project\network\DB\immudb\py_immu\example_grpc\ のコードを使うこと です.
WSLでは Windows の D: は /mnt/d/ に自動マウントされますが、場合によっては No such device のようなエラーが出ることがあります。その場合、以下のコマンドで D: を再マウントすれば、WSL から正常に D: を読み込めるようになります。
sudo umount /mnt/d  # 一度アンマウント
sudo mount -t drvfs D: /mnt/d  # D: を WSL に再マウント

PW: greg1024
この操作をしても、D: に venv が作られるわけではなく、あくまで D: を WSL から正しく使えるようにするだけです。

③ venv をどこで使うべきか
venv は C: (/home/kibiy/venvs/) にあり、D: のコードを実行
この場合、venv は WSLの home/kibiy/venvs/example_grpc/ にある

/mnt/d/ のコードを WSL の Python で動かす
やり方は以下のとおり。
# ① D: を WSL に正しくマウント
sudo umount /mnt/d
sudo mount -t drvfs D: /mnt/d

# ② WSL の `venv` をアクティブにする
source ~/venvs/example_grpc/bin/activate

venv の作成が成功したら、上記のように仮想環境を有効化します。
成功すると (example_grpc) という表示が出るはずです。

# ③ D: のコードを実行する
python /mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc/app_immudb.py
この方法では、WSL の仮想環境 (venv) を使いつつ、D: 内のコードをそのまま実行できます。

# immuDBの起動
C:\Users\kibiy>D:
D:\>cd immuDB
■　D:\immuDB>immudb.exe --config

■　D:\immuDB>immuclient.exe login immudb
Password:immudb
そうすると、
Successfully logged in
immudb user has the default password: please change it to ensure proper security と表示される！

■　D:\immuDB>immuadmin.exe login immudb
Password:immudb
そうすると、
logged in
SECURITY WARNING: immudb user has the default password: please change it to ensure proper security　と表示される！
●　immuclient.exe と immuadmin.exe の違い
・immuclient.exe
→ データの保存・取得 (set / get) を実行するためのツール
・immuadmin.exe
→ データベースの管理 (database list / database create) を行う管理ツール

■　D:\immuDB>immuadmin.exe database list
1 database(s)
-  -------------  ----------  ----------  ------  ----------  ---------  ------------
#  Database Name  Created At  Created By  Status  Is Replica  Disk Size  Transactions
-  -------------  ----------  ----------  ------  ----------  ---------  ------------
1  defaultdb      2025-01-31  systemdb    LOADED  FALSE       6 KB       1
-  -------------  ----------  ----------  ------  ----------  ---------  ------------

■　もし新しいデータベースを作成したい場合：
immuadmin.exe database create mynewdb
そうすると、
database 'mynewdb' {replica: false} successfully created　と表示される。

その後、immuclient.exe でこのデータベースを使用するように変更：
immuclient.exe use mynewdb
そうすると、
Now using mynewdb　と表示される。

■　テストフォルダーへ移動してimmuDBを起動
D:\immuDB>immudb.exe --config D:\city_chain_project\network\DB\config\immudb_config\login\immudb_login_Default_config\immudb_login_Default.toml
これで予め設定していたimmudb.tomlにて起動できる。

#　.tomlファイルにてDBの設定やportの設定やgRPCを有効化などの設定を記載しておく。
dir = "D:\\city_chain_project\\network\\DB\\immudb\\data\\tests\\login\\Default"
address = "192.168.3.8"
port = 3322
metrics-address = "0.0.0.0:9497/metrics"

[grpc]
enabled = true
port = 3322

これで、databaseを指定など一連の設定ができる。

なお、
immuadmin shutdown
もしくは
Ctrl + C でimmuDBはストップできる。

#　immuDBのテスト環境での起動が出来ているか確認
(1) netstat で確認
コマンドプロンプト (cmd) で以下を実行：
netstat -ano | findstr :3322
✅ 結果の例（正常時）
  TCP    0.0.0.0:3322           0.0.0.0:0              LISTENING       12345

(2) immudb_clientを起動
D:\immuDB>immuclient.exe --immudb-address 192.168.3.8 --immudb-port 3322 login newadmin
とするとパスワードの入力を求められる。
Password: immudb　⇒　greg1024 に変更
で入ることができる。

(3) immudb_adminを起動
D:\immuDB>immuadmin.exe --immudb-address 192.168.3.8 --immudb-port 3322 login immudb
とするとパスワードの入力を求められる。
Password: immudb　⇒　greg1024　に変更
で入ることができる。


# 次に、immuDBにgRPCを認識させる
WSL 内で immuDB を起動した（案内通りに進めて、起動できた）
次に VSCode に戻り、仮想環境 (venv) に入り、gRPC 経由でアクセスしようとしている。
今の状態は、Windows側でimmuDBが立ち上がっていて、WSL側では立ち上がっていない ということになる。
そのため、WSLから app_immudb.py を実行しようとすると、WSL側のPythonアプリがWindows側のimmuDBに接続
しようとして失敗する という状態。これを修正していく。
1．Windows側でimmuDBの起動アドレスを確認する
例えば、Windowsのコマンドプロンプトで以下を実行：
hostname -I
もしくは
netstat -ano | findstr 3322
これで immudb.exe がどのIPアドレスで動いているか 確認する。
たとえば 0.0.0.0:3322 や 192.168.3.8:3322 になっていることを確認。

2．WSL側の app_immudb.py の接続設定をWindowsのimmuDBに合わせる
immudb_handler.py で host をWindows側の immudb.exe のアドレス (192.168.3.8 など) に変更：
host = "192.168.3.8"  # Windows側のimmuDBのアドレス
port = 3322

今度は、WSL側（VSCODE側）から下記をやってみる
3️⃣ gRPC サービスの一覧を確認
現在 immuDB が提供している gRPC サービスを確認するため、grpcurl を使ってみてください。
ターミナルで python3 を起動して、その中で実行するべき。
✅ 1. immudb の Python モジュールをインストール
まず、immudb の gRPC 用 Python クライアントがインストールされているか確認します。
(仮想環境が有効になっている状態で以下を実行)
pip list | grep immudb
→ 何も表示されない場合、immudb がインストールされていない。

✅ インストール
pip install immudb-py
pip install --upgrade pip
pip install flask requests grpcio grpcio-tools

# PYTHONPATH の設定
export PYTHONPATH=$PWD
echo 'export PYTHONPATH=$PWD' >> ~/.bashrc
source ~/.bashrc

正しい手順：
python3

・その後、Pythonの対話モードで以下を実行
import grpc
from immudb.grpc.schema_pb2_grpc import ImmuServiceStub
from immudb.grpc.schema_pb2 import LoginRequest

channel = grpc.insecure_channel("192.168.3.8:3322")
stub = ImmuServiceStub(channel)

login_request = LoginRequest(user=b"immudb", password=b"immudb")
response = stub.Login(login_request)
print(response)

・次に試す：Python で immuDB のデータの読み書きをテスト
💾 キー (test_key) に Hello, immuDB! を書き込む
#!/usr/bin/env python3
import grpc
import logging

from immudb.grpc.schema_pb2_grpc import ImmuServiceStub
from immudb.grpc.schema_pb2 import (
    LoginRequest,
    SetRequest,    # SetRequest のフィールドは "KVs"（KeyValue のリスト）となっている
    KeyValue,      # キーと値を格納するメッセージ
    KeyRequest     # Get のリクエスト用。キーは "key"（bytes 型）として指定
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

channel = grpc.insecure_channel("192.168.181.12:3322")
stub = ImmuServiceStub(channel)

login_request = LoginRequest(user=b"immudb", password=b"immudb")
try:
    login_response = stub.Login(login_request)
    logging.info("Login response: %s", login_response)
except grpc.RpcError as e:
    logging.error("Login failed: %s", e)
    exit(1)

metadata = [("authorization", login_response.token)]

set_req = SetRequest(
    KVs=[KeyValue(key=b"test_key", value=b"Hello, immuDB!")],
    noWait=False  # 必要に応じて設定。ここでは待機しない場合は False とする
)
try:
    set_response = stub.Set(set_req, metadata=metadata)
    logging.info("Set response: %s", set_response)
except grpc.RpcError as e:
    logging.error("Set failed: %s", e)

get_req = KeyRequest(key=b"test_key")
try:
    get_response = stub.Get(get_req, metadata=metadata)
    logging.info("Get response: %s", get_response)
    # 返却される Entry メッセージのフィールド名は、通常「v」（value）となっている場合が多いです
    if hasattr(get_response, "v"):
        logging.info("Stored value: %s", get_response.v)
    else:
        logging.error("Get response does not contain expected field 'v'")
except grpc.RpcError as e:
    logging.error("Get failed: %s", e)


・GetRequest を使って保存したデータを取得
データが正しく書き込まれたか確認するには、以下のコードを実行してください。
from immudb.grpc.schema_pb2 import KeyRequest

get_request = KeyRequest(key=b"test_key")

get_response = stub.Get(get_request)

print(get_response)

→ ここで成功すればOK。失敗すれば、次の grpcurl の問題と関連する可能性が高い。

4️⃣ immudb_client.py で gRPC のサービス定義を確認
immudb_client.py で stub を作成する際に、適切な gRPC サービス (immudb.schema.ImmuService) を参照しているか確認してください。
例えば、次のようになっているかをチェック：
self.stub = immudb.schema.ImmuServiceStub(self.channel)
もし immudb.ImmuDBStub になっている場合、バージョンの違いで API 定義が変更された可能性 があります。

5️⃣ grpcurl で Login のリクエストを試す
以下のコマンドを実行し、手動で Login を呼び出してみてください。
grpcurl -plaintext -d '{"user": "immudb", "password": "immudb"}' 192.168.3.8:3322 immudb.schema.ImmuService.Login
もしエラーが出たら、それに応じて immudb_client.py のコードを修正する必要があります。

✅ 次にやること
Python の gRPC クライアント (app_immudb.py) の設定を修正
WSL 側から grpcurl でログインテスト
Python (app_immudb.py) でログイン試行
① app_immudb.py の接続設定を修正
現在の immuDB の IP アドレスは 192.168.181.12 になっているため、以下の設定を変更してください。

変更前 (間違っている可能性がある)
host = "192.168.3.8"  # ← 以前のネットワークのIP
port = 3322
変更後 (正しい設定)
host = "192.168.181.12"  # ← `grpcurl` で確認したIPに修正
port = 3322
これで Python 側の gRPC クライアントが正しい IP に接続できる はずです。

② grpcurl でログインできるかテスト
WSL のターミナルで以下を実行:
grpcurl -plaintext -d '{"user": "aW1tdWRi", "password": "aW1tdWRi"}' 192.168.181.12:3322 immudb.schema.ImmuService.Login

# WSL のパーミッションを修正
Windows で作成したファイルは、WSL から実行できないことがあります。パーミッションを修正することで解決できるかも
chmod +x /mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc/app_immudb.py

その後、もう一度実行してみてください。
python3 /mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc/app_immudb.py

・下記が表示されれば書き込みテストは終了です。
2025-02-11 12:06:19,730 INFO Get response: tx: 2
key: "test_key"
value: "Hello, immuDB!"
revision: 2

2025-02-11 12:06:19,730 INFO Stored value: b'Hello, immuDB!'


# MongoDBの起動
本番環境では、通常MongoDBをOSのサービスとして設定し、サーバーが起動すると自動的にMongoDBも起動するようにします。
・WindowsでMongoDBをサービスとして登録する手順
MongoDBをサービスとしてインストール
以下のコマンドを管理者権限で実行します。
mongod --config "D:\city_chain_project\network\DB\config\mongodb_config\login\mongodb_login_Default_config\mongodb_login_Default.conf" --install

サービスの開始 サービスを起動します。
net start MongoDB

testの場合は、デフォルトポート27017から下記のように入る。（mongoDBの場合）
mongod --dbpath "D:\city_chain_project\network\DB\mongodb\data\tests\login\Default" --port 27017

testの場合は、デフォルトポート3322から下記のように入る。（immuDBの場合）
immud --dbpath "D:\city_chain_project\network\DB\immudb\data\tests\login\Default" --address 127.0.0.1 --port 3322

testは実際にデータをやりとりさせてみる
cargo run --bin main_rsmongodb
cargo test

特徴	cargo run	　　　　　　　　        cargo test
目的	アプリケーションを実行	　　         テストを実行
対象コード	main.rs or [bin] 定義のファイル	 #[test] 属性を持つ関数
テストの実行	実行しない	                 自動テストを実行
ユニットテスト	実行しない	                 実行する
統合テスト	実行しない	                     tests/ フォルダ内のテストを実行
ビルド対象のプロファイル dev プロファイル	  test プロファイル
ドキュメントテストの実行  実行しない	      実行する

1. サービスから停止
Windowsキー + R を押して services.msc を開く。
「MongoDB サービス」を見つけて右クリックし、「停止」を選択。
2. タスクマネージャーで停止
Ctrl + Shift + Esc を押してタスクマネージャーを開く。
「MongoDB サーバー プロセス」を探し、右クリックして「タスクの終了」を選択。
3. PowerShellを使う
以下のコマンドを使用してMongoDBを終了できます：
net stop MongoDB

Stop-Process -Name mongod -Force


#　データフロー設計
```mermaid
graph TD
    %% 送信側のプロセス
    A[送信用index.htmlからトランザクションデータ受信] --> B[app.pyでデータ受信]
    B --> C[municipalityとcontinentの抽出]
    C --> D{大陸の選択}
    D -->|Asia| E[Asia_municipal_chainへ送信]
    D -->|Europe| F[Europe_municipal_chainへ送信]
    D -->|Default| G[Default_municipal_chainへ送信]
    E --> H[send_pendingにトランザクション保存]
    F --> H
    G --> H
    H --> I{ブロック生成条件確認}
    I -->|条件達成| J[ブロック生成]
    J --> K[ブロック承認]
    K --> L[continental_main_chainにブロック転送]
    L --> M[保留リストにブロック保存]

    %% 受信側のプロセス
    M --> N[受信用index.htmlから受信信号受信]
    N --> O[app.pyで受信信号処理]
    O --> P[continental_main_chain経由で保留リストにアクセス]
    P --> Q[10大陸に保留リスト共有]
    Q --> R{該当municipal_chainで受信トランザクション処理}
    R -->|処理成功| S[receive_pendingにトランザクション保存]
    S --> T{ブロック生成条件確認}
    T -->|条件達成| U[ブロック生成]
    U --> V[ブロック承認]
    V --> W[completeに更新]
    W --> X[MongoDBにトランザクション保存]
    X --> Y[後続処理へデータ移行]

    %% 後続処理
    Y --> Z[分析用データベースへの移行]
    Y --> AA[Gossipアルゴリズムによるデータ共有]
    Y --> AB[他のDAppsからのデータ抽出]

### 10. 小松市のAさんから金沢市のBさんに200愛貨を送信する一連の設定
DApps側とMunicipal Chain側の設定を踏まえて、小松市のAさんが金沢市のBさんに200愛貨を送信するための一連のセットアップ手順を再構成します。今回のケースでは、DAppsのFlaskとMongoDB、Municipal ChainのFlaskとMongoDB、さらにAsiaのMongoDBの全てが必要です。以下に、具体的な手順を一からご案内します。

1. 必要なMongoDBインスタンスを起動する
DApps側（デフォルトまたはAsia）のMongoDBインスタンスと、Municipal Chain側のAsia MongoDBインスタンスをそれぞれ起動します。

保存方法:MongoDBはデータをtest_databaseなどの名前でフォルダに直接保存するわけではありません。データはバイナリ形式で、以下のようなファイルに保存されます：
  .wt ファイル: WiredTigerエンジン用のデータファイル。
  journal フォルダ: データの永続性を保証するためのログ。

DApps MongoDB
ポート番号は、設定ファイルに基づいて起動します。ここではデフォルトのMongoDB（ポート27017）を利用しますが、必要に応じてAsiaのMongoDB（10024）も使用可能です。
D:\MongoDB\Server\7.0\bin\mongod.exe --port 27017 --dbpath "D:\data\mongodb\dapps"

Municipal Chain MongoDB (Asia)
D:\MongoDB\Server\7.0\bin\mongod.exe --port 10024 --dbpath "D:\data\mongodb\asia"

2. Flaskアプリのセットアップと起動
DApps Flask
DAppsのFlaskアプリケーションを起動します。環境変数または設定ファイルからポートを決定し、DAppsのFlaskアプリがリクエストを受け取れるようにします。
・Flask CLI（コマンドラインインターフェース）での実行: こちらの方法は、まず環境変数としてFLASK_APPにファイル名を設定し、その後Flask CLIを使ってアプリを実行します。
・追加機能の利用: Flask CLIを使用することで、Flaskが提供する追加機能（デバッグモードの切り替え、サーバーのポート指定、その他の設定）が簡単に利用できます。柔軟にアプリケーションを起動したい場合には、python app.pyを使います。CLIの機能を活用して、複雑な操作やデバッグを行いたい場合には、set FLASK_APP=app.py && flask run --port=1024が便利です。
set FLASK_APP=app.py
flask run --port=1024
（1024はAsia大陸のポート）

Municipal Chain Flask (Komatsu)
set FLASK_APP=app.py
flask run --port=2001

Municipal Chain Flask (Kanazawa)
set FLASK_APP=app.py
flask run --port=2000

3. ファイアウォール設定の確認（必要に応じて）
必要なポート（27017, 10024, 20000,20001, 2001, 2000など）を開放し、通信を許可します。
New-NetFirewallRule -DisplayName "Open MongoDB Port 10024" -Direction Inbound -LocalPort 10024 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Open MongoDB Port 20000" -Direction Inbound -LocalPort 20000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Open MongoDB Port 20001" -Direction Inbound -LocalPort 20001 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Open Flask Port 2001" -Direction Inbound -LocalPort 2001 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Open Flask Port 2000" -Direction Inbound -LocalPort 2000 -Protocol TCP -Action Allow

4. DApps Flask アプリのトランザクション送信
app.pyから、送信リクエストを行います。具体的には、KomatsuのFlaskにアクセスしてトランザクションを処理し、Municipal Chain (KomatsuとKanazawa)とAsia MongoDBにデータが保存されます。
# DAppsでの送信リクエスト (例)
import requests

transaction_data = {
    "sender": "A",
    "sender_municipality": "Asia-Komatsu",
    "receiver": "B",
    "receiver_municipality": "Asia-Kanazawa",
    "amount": 200,
    "continent": "Asia",
    # その他必要なフィールドを追加
}

response = requests.post("http://localhost:2001/send", json=transaction_data)
print(response.json())

5. Municipal Chain側でのトランザクション受信と保存
Komatsu（小松市）のFlaskアプリがデータを受信し、Municipal Chain (Komatsu)側のMongoDBに送信情報が保存されます。その後、AsiaのMongoDBにデータが送信され、全てのチェーンでトランザクションが保持されます。

6. 全体のデータフロー確認とテスト
すべてのFlaskとMongoDBが起動し、必要な通信が可能であることを確認します。
トランザクションデータがMunicipal ChainのFlaskに保存されていることを確認します。
以上で、小松市から金沢市への200愛貨の送信が可能になるはずです。

### 11. 小松市のAさんから金沢市のBさんに200愛貨を送信するmunicipal_chainの実行プログラム
cargo run -- Asia-Komatsu というコマンドは、municipal_chainのRustプログラムを起動して、**Asia-Komatsu**という引数を渡しています。これにより、アジア地域のKomatsu市の設定で、Municipal Chainのプログラムが動作するように設定されています。このプログラムは、以下のような役割を果たします：

Komatsu市の代表者選出とトランザクションの承認:

Asia-Komatsuに特定された代表者リストから、送信者と受信者の代表者が選出され、トランザクションの承認が行われます。
MongoDBとの接続:

municipal_chainのコード内で、Komatsu市用のMongoDBが起動され、愛貨トランザクションの記録や、ペンディング状態のトランザクションを管理します。
送信トランザクションは、Komatsu市のMongoDBに保存され、その後Asiaのコンチネンタルチェーンに渡されます。
Flaskとの連携:

Komatsu市に関連するFlaskのポート（ここでは1024）が開かれており、トランザクションのリクエストを受け付けて処理するために必要です。
コマンド実行時のエラーメッセージと警告
警告メッセージ: cargo runの実行中に多数の警告が表示されていますが、これらは使われていないインポートや未使用の変数に関するもので、直接的な動作には影響しません。
エラー (STATUS_ACCESS_VIOLATION):
これはプログラムのスタックオーバーフローが原因で発生しています。解決策として、プログラムのスレッドスタックサイズを増加させるか、再帰処理やループ構造に無限ループがないか確認する必要があります。
再設定と起動手順の流れ
Rustコードの修正: municipal_chainのコードを再確認し、未使用の変数やデッドコードを削除し、無限ループがないか確認します。
MongoDBとFlaskの起動:
Flaskのポート (1024)とKomatsu市のMongoDB (10024) を開放し、他の必要なDAppsやMunicipal Chainのサービスを立ち上げます。
Komatsu市用に再起動: 上記の修正を行った後に、再度 cargo run -- Asia-Komatsu を実行して、Komatsu市のプログラムが正しく稼働することを確認します。
これで、Komatsu市（小松市）のAさんが送信する愛貨が、Asia地域のMongoDBとFlaskを介してトランザクションとして管理されるようになるはずです。

###　immudbへの書き込み方法
1. immudbの利用について
これでimmuclientを使用してimmudbに接続し、データベース操作を行うことができます。

2. ブロックチェーンからimmudbにデータを書き込む方法
2.1 immudbのアドレス設定
ブロックチェーンのアプリケーションからimmudbにデータを書き込むためには、immudbサーバーのアドレスとポートを正しく設定する必要があります。

デフォルトのアドレスとポート：

アドレス：localhostまたは127.0.0.1
ポート：3322
2.2 アプリケーションからの接続方法
言語ごとのクライアントライブラリ：
immudbは、さまざまなプログラミング言語向けのクライアントライブラリを提供しています。これらを使用して、アプリケーションからimmudbに接続し、データ操作を行うことができます。
Go
Java
Python
Node.js
Rust（もし公式ライブラリがない場合、gRPCを使用して接続可能）

2.3 接続の設定例（Pythonの場合）
ステップ1：Pythonクライアントライブラリのインストール
pip install immudb-py
ステップ2：Pythonコードでの接続
from immudb.client import ImmudbClient

# immudbサーバーのアドレスとポートを指定
client = ImmudbClient("{immudbのアドレス}", port=3322)

# ログイン
client.login("immudb", "immudb")

# データのセット
client.set("mykey", "myvalue")

# データの取得
value, _ = client.get("mykey")
print(value)  # 出力: myvalue
注意点：
{immudbのアドレス}には、immudbサーバーの実際のIPアドレスまたはホスト名を指定します。
Dockerでimmudbを実行している場合、ホストマシンから接続する場合はlocalhostを使用できます。

2.4 Rustからの接続
immudbの公式Rustクライアントライブラリは提供されていない可能性がありますが、gRPCを使用して接続できます。
ステップ1：gRPCクライアントのセットアップ
RustでgRPCを使用するために、tonicやgrpcioなどのライブラリを使用します。

ステップ2：immudbのプロトコル定義を使用
immudbのプロトコルバッファ定義（.protoファイル）を取得し、Rustコード内で使用します。

3. Webインターフェースでデータを確認する方法
immudbには、Webベースの管理コンソールが提供されています。これを使用して、データベースの内容を確認したり、操作を行ったりできます。

3.1 管理コンソールへのアクセス
URL：http://localhost:9497
Dockerでimmudbを起動する際に、ポート9497を公開している必要があります。
⇒　docker run -d --name immudb -p 3322:3322 -p 9497:9497 codenotary/immudb
3.2 ログイン
ユーザー名：immudb
パスワード：immudb
3.3 管理コンソールの機能
データの閲覧：データベース内のキーと値を確認できます。
クエリの実行：GUI上でSQLクエリを実行できます。
統計情報：サーバーの状態や統計情報を確認できます。
3.4 注意事項
テスト用途：

管理コンソールはテストやデバッグに便利ですが、本番環境ではセキュリティ上の理由から適切な認証とアクセス制御を行ってください。
4. ブロックチェーンアプリケーションとの統合
ブロックチェーンからimmudbにデータを書き込むシナリオでは、以下の点を考慮する必要があります。

4.1 データフローの設計
ブロックチェーンイベントのキャプチャ：

スマートコントラクトからのイベントやトランザクションデータをキャプチャします。
ミドルウェアの開発：

ブロックチェーンとimmudbの間にミドルウェアを設け、データを変換・転送します。
4.2 接続設定
アドレスとポートの設定：

ミドルウェアやアプリケーションからimmudbに接続する際、immudbのアドレス（IPアドレスまたはホスト名）とポート3322を指定します。
Docker環境での接続：

同一ホスト内での接続：

アプリケーションがホストマシン上で実行されている場合、localhostを使用してimmudbに接続できます。
Dockerコンテナ間での接続：

アプリケーションもDockerコンテナで実行している場合、同じDockerネットワーク上に配置し、コンテナ名で通信できます。
4.3 セキュリティの考慮
認証情報の管理：

immudbのユーザー名とパスワードを安全に管理します。
TLS/SSLの使用：

通信を暗号化するために、immudbのTLS設定を有効にすることを検討してください。
5. テスト環境での確認
テスト目的でimmudbの動作を確認するには、以下の方法があります。

5.1 管理コンソールの利用
前述の通り、Webブラウザからデータを確認できます。
5.2 CLIツールの使用
immuclientを使用して、コマンドラインからデータ操作や確認ができます。

# データのセット
immuclient set mykey myvalue

# データの取得
immuclient get mykey
5.3 アプリケーションからのログ出力
アプリケーションコード内で、immudbへの書き込みや読み込み結果をログ出力することで、動作確認ができます。

### MongoDBの状態遷移について
トランザクションの状態管理（send, send_pending, receive, receive_pending, complete）は理にかなっており、特にトランザクションの各段階を明確に追跡できるという点で良いアイデアです。

具体的には、以下のようにトランザクションの状態を管理することが考えられます：
1. 送信フロー
状態: send
送信者がトランザクションを生成し、dapps\app.pyからMunicipal Chainに送信するときに、まずMongoDBにsend状態で保存される。
ここでは、トランザクションが送信されたが、Municipal Chainによってまだ承認されていないことを示す。

状態: send_pending
Municipal Chainで承認され、トランザクションがsend_pending状態に移行される。
この状態は、受信者側が受け取る準備が整うまで、つまり受信側からの確認を待っていることを示す。

2. 受信フロー
状態: receive
受信者が受信リクエストを送信すると、dapps\app.pyからMunicipal Chainに送信され、MongoDBにはreceive状態で保存される。
ここでは、受信リクエストが送信されたが、まだMunicipal Chainで承認されていないことを示す。

状態: receive_pending
Municipal Chainで受信が承認されると、receive_pending状態になる。
この状態は、トランザクションがブロックチェーンに取り込まれる準備が整ったことを示す。

3. 最終状態
状態: complete
トランザクションがブロックチェーンに記録され、承認されれば、complete状態に変更される。
これにより、そのトランザクションは完全に処理済みであることが確認できる。

メリット:
各トランザクションの状態を段階的に追跡でき、問題が発生した場合（例えば、承認エラーや処理中断）に適切な対応が取れる。
取引のステータス管理がしやすくなり、どの段階で問題が起きているかを簡単に確認できる。
MongoDBのトランザクションステータスを確認するだけで、トランザクションがどの段階にあるのかを簡単に把握できる。


### GitHubにコードをプッシュして共有する方法を一つずつ説明します。
1. GitHubアカウントの作成
まずは、GitHubアカウントが必要です。まだ持っていない場合は、GitHubでアカウントを作成してください。

2. 新しいリポジトリの作成
GitHubにログインした後、右上の「+」アイコンをクリックし、「New repository」を選択します。
リポジトリ名を入力します（例：city_chain_project）。
「Private」または「Public」を選択します。**「Public」を選ぶと誰でもアクセス可能になり、「Private」**だと限られたユーザーだけがアクセスできます。「Create repository」をクリックします。

3. Gitの初期設定
ローカルの開発環境で次の設定を行いましょう。まず、ターミナルやコマンドプロンプトを開き、以下のコマンドを実行して、Gitのユーザー名とメールアドレスを設定します。
git config --global user.name "Your GitHub Username"
git config --global user.email "your-email@example.com"

4. ローカルリポジトリの初期化
city_chain_projectフォルダに移動します。
cd path/to/your/city_chain_project

Gitの初期化を行います。
git init

5. GitHubリポジトリをローカルリポジトリにリンク
GitHubのリポジトリページで表示される「https://github.com/username/repositoryname.git」のようなURLをコピーします。
ターミナルで次のコマンドを実行してリポジトリを追加します。
git remote add origin https://github.com/username/city_chain_project.git

6. ファイルを追加・コミットする
すべてのファイルをステージングします。
git add .

コミットメッセージを追加してコミットします。
git commit -m "Initial commit"

7. GitHubにプッシュする
次に、ローカルの変更をGitHubにプッシュします。
git push -u origin main

これで、GitHubリポジトリにコードがアップロードされ、共有が完了します。


###　柔軟なデータ構造の採用 : トランザクションデータのモジュール化
固定的なデータ構造を避け、拡張可能なデータモデルを採用することで、新しい科目の追加によるデータ構造の変更を最小限に抑えることができます。

キー-バリュー形式のデータ構造：

トランザクションデータや科目情報をキー-バリューのペアとして保存します。
新しい科目は新たなキーとして追加され、既存のデータ構造を変更する必要がありません。
動的な属性の利用：

可変長の属性リストやマップを使用し、科目情報を柔軟に保持します。
例えば、attributes フィールドを HashMap<String, String> として定義し、新しい科目情報をこのマップに追加します。