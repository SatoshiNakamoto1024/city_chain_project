もちろん「既存の py_immu フォルダを壊さずに、Rust 用に参照したい gRPC サーバー（py_immu_server.py など）を別フォルダに置いて開発する」という方針もアリです。

1. そもそもの問題: 上書きが怖い
python -m grpc_tools.protoc ... でスタブを再生成すると、同じファイル名（immudb_pb2.py, immudb_pb2_grpc.py）に上書きしてしまう。
結果として「いままで py_immu でテストしていたコードを上書きして壊してしまわないか？」という懸念がありますよね。

2. 別フォルダに分離するメリット
既存の py_immu はそのまま残しておいて、これまでのテストを壊さない。
新たに py_rs_immu_connect などのフォルダを作り、py_immu_server.py・immudb_pb2.py・immudb_pb2_grpc.py をまとめる。
このようにすれば、Rust と連携した実装に関しては py_rs_immu_connect 内で独立して管理できるため、既存テストと混ざらず安全。

3. 実際のやり方例
新フォルダを作成
Edit
D:\city_chain_project\network\DB\immudb\
 ├─ py_immu\                  (これまでのテスト用)
 └─ py_rs_immu_connect\          (Rust連携用)
     ├─ py_immu_server.py
     ├─ immudb_pb2.py
     ├─ immudb_pb2_grpc.py
     ├─ __init__.py          (必要なら空ファイル)
     └─ (その他ファイル)

# grpcipのインストール
wsl --install
sudo apt update
sudo apt install python3 python3-pip -y

2．WSL 上で grpcio をインストール
python3 -m venv venv

仮想環境を作成
・Cドライブに venv を作る
・WSL のローカルディレクトリ (~) に新しい仮想環境を作る。
　以下で、"C:\Users\kibiy\venvs\py_rs_immu_connect"というフォルダーが作られる。
  これが重要！D:にvenvを作ってもエラーになるよ！
mkdir -p ~/venvs/py_rs_immu_connect
python3 -m venv ~/venvs/py_rs_immu_connect

まず、出力先 (/mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/) が存在するか確認：
ls -l /mnt/d/city_chain_project/network/DB/immudb/

もし py_rs_immu_connect/ ディレクトリが存在しなければ、作成する：
mkdir -p /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect

Windows 側の D:\city_chain_project\network\DB\immudb\py_rs_immu_connect を WSL で開く
cd /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect

Python インタープリターを開く
python3

gRPC が正しくインストールされているか確認
import grpc
print(grpc.__version__)

・1.70.0　などと表示されればOK

Python インタプリタを終了
exit()

① WSLの venv の現在地
今、venv は WSL の home/satoshi/venvs/py_rs_immu_connect/（つまり C: 内） にあります。
WSL の home フォルダは、Windows の C:\Users\kibiy\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu_*\ 以下にありますが、直接 Windows からアクセスするのは推奨されません。
そのため、Windows から見るときは、エクスプローラーで以下のアドレスを入力：
\\wsl$\Ubuntu\home\kibiy\venvs\py_rs_immu_connect\
で開けます。

venv の状態を確認する
まず、以下のコマンドで venv が正しく作成されているか確認しましょう。
ls -l ~/venvs/py_rs_immu_connect/

正常なら、以下のようなフォルダが見えるはずです。
bin  include  lib  lib64  pyvenv.cfg

② WSL から D: のコードを読み込む
今やりたいことは WSL から D:\city_chain_project\network\DB\immudb\py_rs_immu_connect\ のコードを使うこと です.
WSLでは Windows の D: は /mnt/d/ に自動マウントされますが、場合によっては No such device のようなエラーが出ることがあります。その場合、以下のコマンドで D: を再マウントすれば、WSL から正常に D: を読み込めるようになります。
sudo umount /mnt/d  # 一度アンマウント
sudo mount -t drvfs D: /mnt/d  # D: を WSL に再マウント

PW: greg1024
この操作をしても、D: に venv が作られるわけではなく、あくまで D: を WSL から正しく使えるようにするだけです。

③ venv をどこで使うべきか
venv は C: (/home/kibiy/venvs/) にあり、D: のコードを実行
この場合、venv は WSLの home/kibiy/venvs/py_rs_immu_connect/ にある

/mnt/d/ のコードを WSL の Python で動かす
やり方は以下のとおり。

# ② WSL の `venv` をアクティブにする
source ~/venvs/py_rs_immu_connect/bin/activate

venv の作成が成功したら、上記のように仮想環境を有効化します。
成功すると (py_rs_immu_connect) という表示が出るはずです。そして下記をインストール。
grpcio をインストール

pip install grpcio grpcio-tools
pip install --no-cache-dir grpcio grpcio-tools
pip install requests grpcio grpcio-tools
pip install grpcio-reflection
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
python /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py
この方法では、WSL の仮想環境 (venv) を使いつつ、D: 内のコードをそのまま実行できます。


# 実行前に、immudb_pb2.py , immudb_pb2_grpc.py を作成しておくこと
.proto からスタブを生成 (py_rs_immu_connect ディレクトリで)
cd /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect

カレントディレクトリを py_rs_immu_connect にして実行すると（下記のように）
(py_rs_immu_connect) satoshi@LAPTOP-88SH779D:~$ python -m grpc_tools.protoc \
  -I /mnt/d/city_chain_project/proto \
  --python_out=/mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect \
  --grpc_python_out=/mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect \
  /mnt/d/city_chain_project/proto/schema/immudb.proto

そこにschema/ immudb_pb2.py, schema/ immudb_pb2_grpc.py が生成される。

次に、それらの2つのファイルを、py_rs_immu_connectという1つ上のフォルダーに移動する。
そして、schemaというフォルダーは空になるので削除する。
そして、immudb_pb2_grpc.pyを開いて、
import immudb_pb2 as schema_dot_immudb__pb2　（from schemaを削除）
という文章に変える。
これで、動くようになります。


py_immu_server.py を新しく書く（またはコピーして修正）
# connect_rs_immu/py_immu_server.py
import grpc
from concurrent import futures
import time
import immudb   # pip install immudb-py

import immudb_pb2
import immudb_pb2_grpc

class ImmuServiceServicer(immudb_pb2_grpc.ImmuServiceServicer):
    def __init__(self):
        self.client = immudb.ImmuClient("127.0.0.1:3322")
        self.current_token = None

    # ... (Login/Logout/Set/Get など実装) ...
 
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    immudb_pb2_grpc.add_ImmuServiceServicer_to_server(ImmuServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("[Python] gRPC server started on port 50051.")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
これで py_immu のテストはそのまま残り、connect_rs_immu はRust用に独立運用
Rust 側は「python connect_rs_immu/py_immu_server.py」を起動しているところに接続すればOK。
既存の py_immu ディレクトリのファイルは手を付けず、上書きも発生しない。

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

# ファイアウォール確認
New-NetFirewallRule -DisplayName "Allow WSL gRPC 50051" -Direction Inbound -LocalPort 50051 -Protocol TCP -Action Allow

# 必要に応じて権限を修正する：
もし、ファイルが別のユーザー（例えば root）になっている場合、または適切な読み取り権限が与えられていない場合は、以下のように所有者と権限を変更してください。
たとえば、satoshi ユーザーで起動する場合は：
・まずテスト環境のWSL側で
(myenv) satoshi@LAPTOP-88SH779D:~$ sudo netstat -tulnp | grep 3324
[sudo] password for satoshi:greg1024
sudo mount -t drvfs D: /mnt/d -o metadata
sudo chown -R satoshi:satoshi /home/satoshi/immudb_data/tests/europe
sudo chmod -R 755 /home/satoshi/immudb_data/tests/europe
そしてもう一度やってリッスンを確認する
(myenv) satoshi@LAPTOP-88SH779D:~$ sudo netstat -tulnp | grep 3324
tcp        0      0 127.0.0.1:3324          0.0.0.0:*               LISTEN      17439/immudb

# immuDBを8つ同時に手動で立ち上げておいてテストする
以下は、各大陸ごとに異なる IP アドレス（例：
– default: 127.0.0.1
– asia: 127.0.0.2
– europe: 127.0.0.3）で動作させ、かつユーザー名を「satoshi」に統一する場合の一例です。

【前提】
・WSL 内のループバックインターフェースに追加 IP アドレスを設定する必要があります。
  例）
sudo ip addr add 127.0.0.2/8 dev lo
sudo ip addr add 127.0.0.3/8 dev lo
sudo ip addr add 127.0.0.4/8 dev lo
sudo ip addr add 127.0.0.5/8 dev lo
sudo ip addr add 127.0.0.6/8 dev lo
sudo ip addr add 127.0.0.7/8 dev lo
sudo ip addr add 127.0.0.8/8 dev lo
次のコマンドで現在設定されているIPアドレスを確認できます。
ip addr show dev lo

・immudb の各インスタンスはそれぞれ、対応する IP とポートで起動するようにします。
・設定ファイル（immudb_config.json）の内容を変更します。

# 動作手順（例）
各immuDBインスタンス（例えばAsia用：127.0.0.2:3323、Europe用：127.0.0.3:3324、…）を各自のサーバー（または手動起動）で起動してください。 例：WSL上でそれぞれ

/usr/local/bin/immudb --port 3323 --address 127.0.0.2 --admin-password greg1024 --dir /home/satoshi/immudb_data/tests/asia

/usr/local/bin/immudb --port 3324 --address 127.0.0.3 --admin-password greg1024 --dir /home/satoshi/immudb_data/tests/europe

/usr/local/bin/immudb --port 3327 --address 127.0.0.6 --admin-password greg1024 --dir /home/satoshi/immudb_data/tests/northamerica

/usr/local/bin/immudb --port 3328 --address 127.0.0.7 --admin-password greg1024 --dir /home/satoshi/immudb_data/tests/southamerica

# cdにて実行
(py_rs_immu_connect) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect$ 
python3 /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py

# パーミッションエラーがでたら、WSLから下記をして許可をすること
chmod +x /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py

これらのエラーは、WSL内で使用する Python インタープリター（およびその仮想環境）が、spawn された環境で正しく見つからないために発生します。基本的には、Windows側から WSL を起動する場合、WSL 内の環境（ファイルシステムのパス、環境変数など）が通常の対話型シェルと異なることが原因です。
(py_rs_immu_connect) satoshi@LAPTOP-88SH779D:~$ 
ls -l /home/satoshi/venvs/py_rs_immu_connect/bin/python3
とすると、下記のように表示されればＯＫ
lrwxrwxrwx 1 satoshi satoshi 16 Feb 24 06:17 /home/satoshi/venvs/py_rs_immu_connect/bin/python3 -> /usr/bin/python3

(py_rs_immu_connect) satoshi@LAPTOP-88SH779D:~$ 
ls -l /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py
とすると、下記のように表示されればＯＫ
-rwxrwxrwx 1 root root 9664 Feb 26 07:10 /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py

# 「No such device (Errno 19)」エラー:
これは、指定されたパスが存在しない、またはアクセスできない（つまり「デバイス」が見つからない）場合に発生します。spawnされたプロセスが、/mnt/d/city_chain_project/… のパスを解決できず、結果として「No such device」となっています。

対策方法
手動でWSLからファイルにアクセスできるか確認する
Windowsのコマンドプロンプト（またはPowerShell）から以下のコマンドを実行してみてください：
C:\Windows\System32\wsl.exe -d Ubuntu ls -l /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py

もしこれで正しくファイルがリストされれば、WSL自体は正しくマウントされています。
もしエラーが出る場合、WSLの/mnt/dのマウント設定がspawn環境で反映されていない可能性があります。

# WSLの設定ファイルを再確認する
すでに対話型シェルではファイルが見えているので、/etc/wsl.confは正しく設定されているようですが、spawnされたプロセスに反映されるか確認するため、必ずPowershellから下記のコマンドにて
PS C:\WINDOWS\system32> wsl.exe --shutdown
でWSLを完全に再起動してください。

# immuclient をgo言語経由でインストールしたので、操作可能となる
下記のように書き込みテストもパスする
(py_rs_immu_connect) satoshi@LAPTOP-88SH779D:~/immudb$ 
immuclient set my_key "Hello, immudb!" --immudb-address=127.0.0.2 --immudb-port=3323
immuclient get my_key --immudb-address=127.0.0.2 --immudb-port=3323
tx:       1
rev:      1
key:      my_key
value:    Hello, immudb!
tx:       1
rev:      1
key:      my_key
value:    Hello, immudb!


# cargo runの前にポートプロキシ設定
(py_rs_immu_connect) satoshi@LAPTOP-88SH779D:~$ ip a
このコードでポートプロキシを確認する。

あなたは PowerShell で以下のポートプロキシを設定しました：
netsh interface portproxy add v4tov4 listenport=50051 listenaddress=127.0.0.1 connectport=50051 connectaddress=172.31.101.192 (←　ネットワークによって変える)
ポートプロキシ (netsh) を 127.0.0.1:50051 → 172.31.101.192:50051 に設定

Rust 側で transport error が発生した場合！
予想される問題点
・ポートプロキシの設定が正しく適用されていない可能性
・WSL 側で 50051 の gRPC サーバーが正しくリッスンしていない
・Windows ファイアウォールが gRPC 通信をブロックしている可能性
・Python の gRPC サーバーが IPv6 ([::]:50051) でしかリッスンしていない

# WSLのrootに入って50051が正しくリッスンしているか確認
・(py_rs_immu_connect) satoshi@LAPTOP-88SH779D:~$ 
sudo su
netstat -tulnp | grep 50051

・root@LAPTOP-88SH779D:/home/satoshi# 
wsl sudo netstat -tulnp | grep 50051

・root@LAPTOP-88SH779D:/home/satoshi# 
ps aux | grep py_rs_immu_server.

をすると下記になれば、正しくリッスン出来ていない証拠。
root        8143  0.0  0.0   4100  2024 pts/3    S+   04:35   0:00 grep --color=auto py_rs_immu_server.py


#　Windows側から正しくリッスンしているか確認（powershell）
PS D:\city_chain_project\network\DB\immudb\rs_immu> netsh interface portproxy show all             

ipv4 をリッスンする:         ipv4 に接続する:

Address         Port        Address         Port
--------------- ----------  --------------- ----------
127.0.0.1       50051       172.31.101.192  50051

PS D:\city_chain_project\network\DB\immudb\rs_immu> Test-NetConnection -ComputerName 127.0.0.1 -Port 50051
>>
ComputerName     : 127.0.0.1
RemoteAddress    : 127.0.0.1
RemotePort       : 50051
InterfaceAlias   : Loopback Pseudo-Interface 1
SourceAddress    : 127.0.0.1
TcpTestSucceeded : True

これにより、Windows の 127.0.0.1:50051 への接続が、WSL 上の Python サーバー（IP: 172.28.123.45, ポート 50051）に転送されるようになっています。


#　cargo run を実行した結果
PS D:\city_chain_project\network\DB\immudb\rs_immu> cargo run

Logged in, token: asia_immudb_7bbc1f5aeb5b4158abbc8cb4f2c56464
[Rust] Set Success: key=test_key value=[72, 101, 108, 108, 111, 32, 102, 114, 111, 109, 32, 82, 117, 115, 116, 33]
Set response: success=true, message=Data stored
[Rust] Get Success: key=test_key value=Hello from Rust!
[Rust] Get Success: key=test_key value=Hello from Rust!
MultiSet response: success=true, message=MultiSet successful
Scanned items:
Key: test_key, Value: Hello from Rust!
Logout response: success=true, message=Logout OK

となればOKです。


# 本番環境へ向けて
本番環境でgRPC経由の超高速並列処理を実現するためには、テスト環境と比べていくつかの最適化やアーキテクチャ上の工夫が必要になります。以下のポイントを検討してください。

1. サーバーとクライアントの最適化
非同期処理の活用:
Pythonならgrpc.aioや、Rustならtonicの非同期サポートを最大限に活用し、I/O待ちやネットワーク遅延を最小限にする。これにより、大量のリクエストを同時に処理できます。

スレッドプールやコネクションプールの調整:
gRPCサーバー・クライアント両方で、内部のスレッドプールや接続管理を適切にチューニングする。たとえば、CPUコア数に合わせたスレッド数の設定や、コネクション再利用の仕組みを導入することで、スループットが向上します。

2. 水平スケーリングと負荷分散
複数インスタンスの展開:
immudbサーバー自体をコンテナやKubernetes上で水平スケーリングし、リクエストを複数のサーバーに分散させる。これにより、1台あたりの負荷を下げ、全体としての並列処理能力を向上させます。

ロードバランサの利用:
gRPCの負荷分散は、外部のロードバランサ（Envoy、NGINX、KubernetesのServiceなど）を利用することで、複数のサーバー間にリクエストを均等に振り分けることができます。

3. ネットワークとハードウェアのチューニング
低レイテンシなネットワーク:
本番環境では、ネットワーク遅延がパフォーマンスのボトルネックになるため、専用ネットワークや高速な通信インフラを整備する。たとえば、クラウドプロバイダーの高速ネットワークオプションや、オンプレミスなら専用回線の利用を検討してください。

高性能なハードウェア:
データベース処理やインデックス作成などの内部処理が高速に行われるよう、SSD、十分なメモリ、最新のCPUを搭載したサーバーを利用する。

4. モニタリングとリソース管理
パフォーマンスモニタリング:
PrometheusやGrafanaなどのツールを使い、gRPCサーバーやimmudbのメトリクス（リクエスト数、レスポンスタイム、エラー率など）を常に監視し、必要に応じてリソースを調整する。

ログとトレース:
分散トレーシング（OpenTelemetryなど）を導入して、並列処理の各段階でどこにボトルネックがあるかを把握する。これにより、システム全体のパフォーマンス改善が可能になります。

5. Docker/Kubernetes の利用（参考例）
公式Dockerイメージ（codenotary/immudb）を使えば、環境構築が統一され、簡単に複数インスタンスのデプロイとスケーリングが可能です。例えば、Kubernetesで以下のような構成を組むことが考えられます。

Deployment: immudbサーバーのDeploymentを複数レプリカで構築
Service: gRPC用のClusterIPやLoadBalancerタイプのServiceで外部からのアクセスを集約
Horizontal Pod Autoscaler: リソース使用状況に応じて自動的にスケールアウト
このように、DockerやKubernetesを利用すると、複雑な並列処理環境を比較的容易に構築できます。

まとめ
非同期処理やスレッド/コネクションプールのチューニングでgRPC通信の高速化を図る。
水平スケーリングとロードバランシングにより、リクエストを複数のimmudbインスタンスに分散させる。
低レイテンシなネットワークと高性能なハードウェアを整備し、全体のパフォーマンスを向上させる。
モニタリングとトレースでシステムの状態を常に把握し、問題があれば迅速に対応する。
Docker/Kubernetes の利用で、環境構築やスケーリングを自動化し、安定した運用を実現する。
これらの対策を組み合わせることで、本番環境でもgRPCを使った超高速並列処理が可能となり、コードもエラーなく動作するようになるでしょう。