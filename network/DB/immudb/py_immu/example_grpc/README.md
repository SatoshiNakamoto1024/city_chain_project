#　各モジュールを改めて整理した例になります。
以下の設計方針を採用しています。

■　設定ファイル（immudb_config.json）
　各大陸ごとに「host」「port」「username」「password」「database」を定義しており、全モジュールがこれを参照します。

■　immudb_handler.py
　・コンストラクタで受け取った設定（辞書）をもとに、接続先（ホスト:ポート）に対して immudb.ImmudbClient を生成し、ログイン後に論理データベースを選択する。
　
■　app.py
　・Flaskのエンドポイントは最小限にし、リクエストパラメータに応じて、設定ファイルから該当する「大陸（接続先）」の immudb_handler のインスタンスをキャッシュし、DB操作関数を呼び出す。
　
■　immudb_client.py
　・gRPCクライアントとして、設定ファイルから該当する接続情報を読み込み、grpc チャンネルを作成し、ログイン・書き込みなどの操作を行う。
　
■　app_immudb.py
　・gRPCサーバーとして、同様に設定ファイルを読み込み、各大陸ごとの immudb クライアントを生成し、各種操作（Login, Set, Get, MultiSet, Scan, Delete）を gRPC 経由で提供する。
　 下記に各モジュールの具体例を示します。


# grpcipのインストール
wsl --install
sudo apt update
sudo apt install python3 python3-pip -y

2．WSL 上で grpcio をインストール
python3 -m venv venv

仮想環境を作成
・Cドライブに venv を作る
・WSL のローカルディレクトリ (~) に新しい仮想環境を作る。
　以下で、"C:\Users\kibiy\venvs\example_grpc"というフォルダーが作られる。
  これが重要！D:にvenvを作ってもエラーになるよ！
mkdir -p ~/venvs/example_grpc
python3 -m venv ~/venvs/example_grpc

まず、出力先 (/mnt/d/city_chain_project/network/DB/immudb/example_grpc/) が存在するか確認：
ls -l /mnt/d/city_chain_project/network/DB/immudb/

もし example_grpc/ ディレクトリが存在しなければ、作成する：
mkdir -p /mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc

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

# ② WSL の `venv` をアクティブにする
source ~/venvs/example_grpc/bin/activate

venv の作成が成功したら、上記のように仮想環境を有効化します。
成功すると (example_grpc) という表示が出るはずです。そして下記をインストール。
grpcio をインストール

pip install grpcio grpcio-tools
pip install --no-cache-dir grpcio grpcio-tools
pip install requests grpcio grpcio-tools
pip install immudb-py
pip install flask

# ① D: を WSL に正しくマウント
sudo mount -t drvfs D: /mnt/d

# /mnt/d が無いからマウントできない対処法
(A) もう一度ディレクトリを作る
sudo mkdir /mnt/d
sudo mount -t drvfs D: /mnt/d

3．Ubuntu のパッケージを最新化
sudo apt update && sudo apt upgrade -y
  ID:satoshi
  PW:greg1024

Python と venv をインストール
sudo apt install python3 python3-pip python3-venv -y

# ③ D: のコードを実行する
python /mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc/test_app.py
この方法では、WSL の仮想環境 (venv) を使いつつ、D: 内のコードをそのまま実行できます。

# ディレクトリ構成
D:\city_chain_project\network\DB\immudb\py_immu\example_grpc\
  ├─ py_immu_server.py     <-- サーバー本体(非同期gRPC)
  ├─ test_app.py           <-- Python で並行テストを行うスクリプト
  ├─ immudb.proto          <-- (省略) gRPC 定義、python 用にコンパイル済み想定
  ├─ immudb_pb2.py         <-- protoc で生成済み
  ├─ immudb_pb2_grpc.py    <-- protoc で生成済み
  └─ ... (その他)

#　以下に、高負荷な並列アクセスを想定した改良版コードを提示。
ポイントは次のとおりです。

・サーバー (py_immu_server.py) はフル非同期化
Python の asyncio + gRPC AsyncIO サーバーを使用。
immudb-py は同期ライブラリですが、サーバー側では loop.run_in_executor(None, ...) でスレッドプールを用い、並列性を確保しています。ログインや Set/Get/Scan など全メソッドを非同期 async def + await で定義し、複数のクライアントから同時にアクセスが来てもブロッキングを最小化 します。

・サーバーでのセッション管理
SESSIONS は（トークン → 大陸）というスレッド安全な辞書ではありませんが、Python の dict は単一スレッドからの操作ならスレッド安全に動きます。gRPC AsyncIO サーバー内では一度に1スレッドに dispatcher が動くわけではなく（複数タスクが同時に走る可能性あり）、しかし CPython の GIL と run_in_executor の切り替えで競合しにくいです。大量アクセス想定時は asyncio.Lock や外部のキー・バリュー型ストアを使う選択肢もありますが、ここではシンプルにこのままにします。

・テスト (test_app.py) では
サブプロセスでサーバーを起動後、Python の immudb クライアントを使ってテスト。
並行アクセステストの例として asyncio を活用し、asyncio.gather(...) で複数の書き込み・読み込みを同時に行う例を示します。これにより超高速並列処理(Python からの複数同時アクセス)を簡易的に確認できます。Rust 側からのアクセスも同時に行うことは可能で、サーバーは同じ 50051 ポートで待機しています。

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
D:\immuDB>immuclient.exe --immudb-address 192.168.3.8 --immudb-port 3322 login immudb
とするとパスワードの入力を求められる。
Password: immudb
で入ることができる。

(3) immudb_adminを起動
D:\immuDB>immuadmin.exe --immudb-address 192.168.3.8 --immudb-port 3322 login immudb
とするとパスワードの入力を求められる。
Password: immudb
で入ることができる。

(4) 複数のimmudbを同時に起動（テスト時）
(example_grpc) satoshi@LAPTOP-88SH779D:~$ 
下記のように記載すれば、同時に開くことが出来る。
immudb.exe --config D:\city_chain_project\network\DB\config\immudb_config\login\immudb_login_Default_config\immudb_login_asia.toml --port 3323 --metrics-server-port 9498 --address 127.0.0.1 

immudb.exe --config D:\city_chain_project\network\DB\config\immudb_config\login\immudb_login_Default_config\immudb_login_europe.toml --port 3324 --metrics-server-port 9499 --address 127.0.0.2 

immudb.exe --config D:\city_chain_project\network\DB\config\immudb_config\login\immudb_login_Default_config\immudb_login_northamerica.toml --port 3327 --metrics-server-port 9502 --address 127.0.0.5 

immudb.exe --config D:\city_chain_project\network\DB\config\immudb_config\login\immudb_login_Default_config\immudb_login_southamerica.toml --port 3328 --metrics-server-port 9503 --address 127.0.0.6 

（5）ポートが開いているかをこれで確認
ss -tulnp | grep immudb

 (6)Windows ファイアウォール
もし 3324 のポートがブロックされていると、接続に失敗する。
netstat -ano | findstr LISTEN で、ポートがすでに使用されていないか確認。


✅ Flask (app.py) 側の動き
1. Flask サーバーのポートとアドレス
Flask アプリは、Web サービスとして動作します。

例：
app.run(host="0.0.0.0", port=5002, debug=True, use_reloader=False)
このコードは、Flask アプリがどのネットワークインターフェイスで待ち受け（リッスン）するかと、どのポート番号でアクセスを受け付けるかを指定しています。
host="0.0.0.0"
→ サーバーのすべてのネットワークインターフェイスでアクセスを受け付ける（外部からのアクセスを許可）。
port=5002
→ この Flask アプリはポート 5002 で動作しているため、ブラウザなどからは
http://<サーバーのIP>:5002/ という URL でアクセスします。
つまり、Flask は「Web API」や「Webフォーム」を提供する部分であり、そのポート（ここでは 5002）はクライアントが HTTP リクエストを送る先の番号です。

2. immuDB の接続先（大陸ごとの DB インスタンス）
一方、immuDB はデータベースサーバーであり、Flask アプリとは別のプロセス（または別のサーバー）で動いています。設定ファイル（たとえば immudb_config.json）には、各「大陸」に対応する immuDB インスタンスの接続情報が記載されています。

例えば、設定ファイルの一部：

json
{
  "Asia": {
    "host": "immudb-asia",
    "port": 3323,
    "username": "immudb",
    "password": "greg1024",
    "database": "asia"
  },
  "default": {
    "host": "defaultdb",
    "port": 3322,
    "username": "immudb",
    "password": "greg1024",
    "database": "default"
  }
}
「Asia」 の場合：
immuDB サーバーは immudb-asia というホスト名で、ポート 3323 で動作しており、論理データベースとして "asia" を使用します。
「default」 の場合：
同様に、defaultdb というホスト（またはサービス名）でポート 3322 を使用し、論理データベース "default" を利用します。
これら immuDB サーバーは、gRPC や独自のプロトコルで通信を行うため、Flask アプリから直接 HTTP でアクセスするのではなく、内部で「immudb_handler.py」や「immudb_client.py」がこれらの接続情報を使ってアクセスします。

3. Flask アプリと immuDB との連携の仕組み
3.1. Flask アプリ（app.py）の役割
Flask アプリは、外部（クライアント）からの HTTP リクエストを受け付け、適切なエンドポイントで処理を行います。
リクエストの中に「sender_continent」などのパラメータがある場合、どの immuDB インスタンスに対して処理を行うかを判断します。
例として、/store_transaction エンドポイントでは、リクエストボディから "sender_continent" を読み取り、
sender_continent = data.get("sender_continent", "default")
db_handler = get_db_handler(sender_continent)
として、設定ファイルからその大陸に該当する immuDB の接続情報を取得し、ImmuDBHandler インスタンスを生成またはキャッシュから取得します。
3.2. immuDB ハンドラー（immudb_handler.py）の役割
受け取った設定（たとえば Asia の場合は immudb-asia:3323 など）を使って、immudb クライアントを生成し、ログインやデータベース選択（useDatabase）を行います。
その結果、Flask アプリからはこのハンドラー経由で immuDB に対する操作（書き込み、読み込み、スキャンなど）が実行されます。
3.3. ポート番号の違いのポイント
Flask アプリのポート（例: 5002）
→ これは HTTP リクエストを受け付けるためのポート番号です。
→ ブラウザや API クライアントはこのポートにアクセスします。

immuDB サーバーのポート（例: 3323, 3324, 3327, 3328, 3322 など）
→ これは immuDB が gRPC またはその専用プロトコルで通信するためのポート番号です。
→ immudb_handler.py や immudb_client.py がこのポート番号を使って、各 DB インスタンスにアクセスします。

まとめると：

Flask アプリは外部の HTTP クライアントと通信するためのゲートウェイであり、そのポートは（例: 5002）で設定されます。
immuDB は各大陸ごとに異なるポートで動作し、Flask アプリ内のハンドラーがリクエスト内容に応じて、適切な immuDB インスタンス（たとえば Asia は 3323、Europe は 3324 など）にアクセスしてデータの保存や取得を行います。
このように、両者は全く異なる通信チャネルを使っています。Flask は HTTP/HTTPS で通信し、immuDB は gRPC（または専用のバイナリプロトコル）で通信します。したがって、Flask のポート設定と immuDB のポート設定は独立しており、相互に干渉するものではありません。ただし、Flask アプリ側で、どの immuDB インスタンスに接続するかを設定ファイルやリクエストパラメータで明確に切り替える必要があります。

4. 具体例
例：
設定ファイル immudb_config.json による immuDB インスタンスの設定：

Asia: immudb-asia:3323, 論理 DB: "asia"
Europe: immudb-europe:3324, 論理 DB: "europe"
NorthAmerica: immudb-northamerica:3327, 論理 DB: "northamerica"
SouthAmerica: immudb-southamerica:3328, 論理 DB: "southamerica"
default: defaultdb:3322, 論理 DB: "default"
Flask アプリ（app.py）の設定：

Flask アプリは host="0.0.0.0"、port=5002 で起動するため、外部からは http://<サーバーIP>:5002/ にアクセス。
エンドポイントで、リクエスト内に "sender_continent": "Asia" と指定された場合、get_db_handler("Asia") が呼ばれ、設定ファイルから Asia 用の immuDB の接続情報（immudb-asia:3323、論理 DB: "asia"）を使って DB ハンドラーを生成します。
その後、Flask アプリは immuDB ハンドラー経由で、Asia の immuDB に対してデータの書き込みや読み出しの処理を行います。

まとめ
Flask のポート（例: 5002） は、HTTP サーバーとしてのアクセス先を決定します。外部クライアントはこのポートに対してリクエストを送ります。
immuDB のポート は、各 immuDB インスタンスが gRPC などの専用プロトコルで通信するためのもので、設定ファイルで指定されています。これらは Flask アプリ内のモジュール（immudb_handler.py や immudb_client.py）で利用され、リクエストの「sender_continent」に応じて接続先が切り替わります。
Flask アプリは、受け取ったリクエストから「どの大陸の immuDB にアクセスするか」を判断し、その情報をもとに設定ファイルから接続情報を取り出して、適切な immuDB ハンドラー（ImmuDBHandler インスタンス）を利用する設計になっています。
この仕組みを理解することで、例えば将来的に認証（login）、ブロックチェーン機能（Dpos、ntru など）、その他のモジュールと連携させる際にも、各モジュールがそれぞれ適切なデータベースインスタンスにアクセスできるように設計できるようになります。

以上が、Flask サーバーのアドレスと immuDB の接続先（大陸ごと）の関係の詳細な解説です。



# 次に、immuDBにgRPCを認識させる
WSL 内で immuDB を起動した（案内通りに進めて、起動できた）
次に VSCode に戻り、仮想環境 (venv) に入り、gRPC 経由でアクセスしようとしている。
今の状態は、Windows側でimmuDBが立ち上がっていて、WSL側では立ち上がっていない ということになる。
そのため、WSLから app_immudb.py を実行しようとすると、WSL側のPythonアプリがWindows側のimmuDBに接続
しようとして失敗する という状態。これを修正していく。
1．Windows側でimmuDBの起動アドレスを確認する
例えば、Windowsのコマンドプロンプトで以下を実行：
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
grpcurl -plaintext -d '{"user": "aW1tdWRi", "password": "aW1tdWRi"}' 192.168.181.12:3322 immudb.schema.（小松タリーズ）
grpcurl -plaintext -d '{"user": "aW1tdWRi", "password": "aW1tdWRi"}' 192.168.3.8:3322 immudb.schema.（自宅）
ImmuService.Login

#　immudb_pb2.py, immudb_pbs_grpc.py の生成
カレントディレクトリを example_grpc にして実行すると（下記のように）
(example_grpc) satoshi@LAPTOP-88SH779D:~$ python -m grpc_tools.protoc \
  -I /mnt/d/city_chain_project/proto \
  --python_out=/mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc \
  --grpc_python_out=/mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc \
  /mnt/d/city_chain_project/proto/schema/immudb.proto

そこにschema/ immudb_pb2.py, schema/ immudb_pb2_grpc.py が生成される。

次に、それらの2つのファイルを、example_grpcという1つ上のフォルダーに移動する。
そして、schemaというフォルダーは空になるので削除する。
そして、immudb_pb2_grpc.pyを開いて、
import immudb_pb2 as schema_dot_immudb__pb2　（from schemaを削除）
という文章に変える。
これで、動くようになります。

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

# Python からの gRPC 接続
Python 側（Flask app.py や immudb_handler.py など）は、app_immudb.py の gRPC を経由して immuDB に接続するため、基本的に gRPC サーバーの 50051 にリクエストを送る設計でOK です。

Flask (5001) → app_immudb.py (50051) → immuDB (3322 など)
Rust (50051 に gRPC 送信) → app_immudb.py (50051) → immuDB (3322 など)

■　競合するケース
もし Rust も Python も 50051 を使っていて、

RustがgRPCサーバーを別途立てている
Pythonのapp_immudb.pyが50051でgRPCサーバーを立てている
この場合、競合するので、 Python用（例えば 50052）と Rust用（50051）で分けるのがベスト です。


# ディレクトリを WSLネイティブ(ext4) の場所にする
DBの運用上、/mnt/c / /mnt/d のようなWindowsドライブではなく、~/ や /var/lib/ 下のWSLネイティブ領域にデータを置く方が安定します。
IMMUDB_INSTANCES = {
    "default": {
        "port": 3322,
        "dir": "/home/satoshi/immudb_data/tests/defaultdb"
    },
    "asia": {
        "port": 3323,
        "dir": "/home/satoshi/immudb_data/tests/asia"
    },
    # ... etc ...
}
として、事前に

mkdir -p ~/immudb_data/tests/defaultdb
mkdir -p ~/immudb_data/tests/asia
...
を用意したうえで test_app.py を実行すれば、DrvFS特有の問題が解消される場合が非常に多いです。

実行手順
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. immudb.proto
immudb_pb2.py / immudb_pb2_grpc.py が生成される。
python py_rs_immu_server.py でサーバー起動 (または別プロセスから spawn しても良い)
python test_app.py 実行 → コンソールに [TEST] Logged in (asia)..., [single_test] ..., [4-Continent Test] ... と出力され、A->B, C->D の送金記録が書き込まれる。

#　サーバー起動
(example_grpc) satoshi@LAPTOP-88SH779D:~$ python /mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc/py_immu_server.py
===== PY_RS_IMMU_SERVER (DApps, concurrency-ready) STARTUP =====
2025-03-02 08:03:47,676 [INFO] Created immuDB client for default at 127.0.0.1:3322
2025-03-02 08:03:47,677 [INFO] Created immuDB client for asia at 127.0.0.2:3323
2025-03-02 08:03:47,678 [INFO] Created immuDB client for europe at 127.0.0.3:3324
2025-03-02 08:03:47,679 [INFO] Created immuDB client for australia at 127.0.0.4:3325
2025-03-02 08:03:47,680 [INFO] Created immuDB client for africa at 127.0.0.5:3326
2025-03-02 08:03:47,681 [INFO] Created immuDB client for northamerica at 127.0.0.6:3327
2025-03-02 08:03:47,683 [INFO] Created immuDB client for southamerica at 127.0.0.7:3328
2025-03-02 08:03:47,685 [INFO] Created immuDB client for antarctica at 127.0.0.8:3329
2025-03-02 08:03:47,686 [INFO] Async gRPC server started on port 50051.

#　テスト実行
(example_grpc) satoshi@LAPTOP-88SH779D:~$ python /mnt/d/city_chain_project/network/DB/immudb/py_immu/example_grpc/test_app.py
[TEST] Logged in (asia) => token=asia_immudb_e3ba68aa217b4eb5a1f7c7edaab0c618
[single_test] Start
[single_test] Set => success=True, msg=Data stored
[single_test] Get => b'Hello from Python single_test'
[single_test] MultiSet => success=True, msg=MultiSet successful
[single_test] Scan => found 1 items
   Key=b'test_key', Value=b'Hello from Python single_test'
[single_test] Done
[TEST] Logged out (asia).
[4-Continent Test] Asia DB => b'A(asia) -> B(europe): 100harmony tokens'
[4-Continent Test] EuropeDB => b'B(europe) received 100harmony tokens from A(asia)'
[4-Continent Test] NorthDB => b'C(north) -> D(south): 300harmony tokens'
[4-Continent Test] SouthDB => b'D(south) received 300harmony tokens from C(north)'
[4-Continent Test] Done (A->B, C->D)

これでOKです。