### 1. ポートの説明
flask_port: これは大陸レベルでのFlaskサーバーのポートです。つまり、大陸全体を管理するメインチェーン（Continental Main Chain）でFlaskサーバーがリッスンするポートです。

city_port: これは市町村チェーン（Municipal Chain）での通信に使われるポートです。このポートは、市町村のブロックチェーンノードがリッスンするために使用され、市町村間のブロックチェーン通信に使われます。

city_flask_port: これは、市町村レベルで動作するFlaskサーバーのポートです。DAppsや他のサービスが市町村チェーンと通信するときに使用されます。

したがって、flask_portは大陸レベル、city_portは市町村のブロックチェーン通信、city_flask_portは市町村レベルのFlaskサーバー用です。

### 2. 全体の流れとポートの役割
 index.htmlからapp.pyへデータ送信
index.htmlのフォームから送信ボタンを押すと、JavaScriptによってトランザクションデータがapp.pyに送信されます。
使用ポート: app.pyのFlaskサーバーがリッスンしているポート（flask_port）。たとえば、大陸が「Asia」の場合、municipalities.jsonに設定された 1024 が使われます。

 app.pyからmunicipal_chainへデータ送信
app.pyはデータを受信後、送信者と受信者の市町村データに基づいて、municipal_chainの適切なURLを構築し、データをPOSTリクエストとして送信します。
このとき、municipal_chainが待ち受けているポート（city_port）が使われます。たとえば、Taipeiのcity_portは 20000 です。

 municipal_chainでデータ受信
municipal_chain側のRustプログラムがcity_port（例: 20000）でトランザクションデータを受け取り、ブロックチェーンへの記録やDPoS承認などの処理を行います。

 具体的な流れ
index.html → (送信) → app.py: flask_port（例: 1024）
app.py → (POSTリクエスト) → municipal_chain: city_port（例: 20000）

 ポイント
flask_port は、ユーザーが index.html を通して app.py にアクセスするときに使用されるポートです。
city_port は、app.py から municipal_chain にデータを送るときに使われるポートです。
このように、index.htmlからのフロントエンド通信には flask_port が、バックエンドの municipal_chain 通信には city_port が使われています。

### 3. ポートの開き方
まずは、今のWiFIのアドレスを知る。
Windows のポートフォワーディングを設定する方法：

WSL の IP アドレスを確認する
WSL ターミナルで以下のコマンドを実行してください：
hostname -I

例えば、172.28.123.45 という IP が返ってくるとします。

Windows の PowerShell（管理者権限）でポートプロキシを設定する
次のコマンドを実行して、Windows の 127.0.0.1:50051 への接続を WSL の IP アドレスに転送します：
netsh interface portproxy add v4tov4 listenport=50051 listenaddress=127.0.0.1 connectport=50051 connectaddress=172.28.123.45
これにより、Windows の Rust クライアントが http://127.0.0.1:50051 に接続すると、自動的に WSL のサーバー（IP: 172.28.123.45, ポート: 50051）に転送されます。


ポートは、管理者としてPowershellに入り、以下のように記載することで、windowsのファイアウォール：Port 20000 を開くことができる。
これは、他のサーバーやクライアントがポート 20000 を通じて接続する必要がある場合です。通常、APIサーバー（Flaskサーバーなど）やデータベースサーバーが外部と通信するために特定のポートを開放することが求められます。
PS C:\WINDOWS\system32> New-NetFirewallRule -DisplayName "Open Port 20000" -Direction Inbound -LocalPort 20000 -Protocol TCP -Action Allow

Flaskポートの開き方は下記のとおり（Kanazawaの場合）
上記のNew-NetFirewallRule は外部からのアクセスを許可します。下記のflask run --port=2000 は、Flaskアプリケーションが指定したポートで動作を開始します。両者は別の役割を果たしているので、外部からの接続が必要な場合には 両方の設定が必要です。つまり、Flaskアプリを指定ポートで起動し、さらにそのポートへの外部アクセスを許可するためにファイアウォールでポートを開ける必要があります。
export FLASK_APP=app.py
flask run --port=2000

MongoDBを起動するのは下記のとおり（Asiaの場合）
D:\MongoDB\Server\7.0\bin\mongod.exe --config "D:\city_chain_project\config\mongodb_Asia.conf"

MongoDBの稼働チェックは下記のとおり（10024の場合）
mongo --port 10024 --eval "db.stats()"

immudbの場合は、下記のようにポートを開く。
⇒Dockerでimmudbを起動する際に、ポート9497を公開している必要があります。
docker run -d --name immudb -p 3322:3322 -p 9497:9497 codenotary/immudb

Dockerでimmudbを実行する際に、フォルダを指定して永続化するためには、-vオプションを使ってホストマシンのフォルダをコンテナ内のフォルダにマウントする必要があります。以下はその例です。
docker run -d --name immudb -p 3322:3322 -p 9497:9497 -v /path/to/local/folder:/var/lib/immudb codenotary/immudb

# 全体をまとめたテストスクリプト例
テスト時には以下のようなスクリプトを作成して、すべての大陸と市町村を対象に一括でテストを実行できるようにします。
・起動スクリプト例
docker-compose up -d --build

・テスト実行 (例)
python run_tests.py  # 各大陸チェーンと市町村チェーンへのトランザクション送信テストを実行

・終了
docker-compose down


# immudb-address と host address の違い
--immudb-address と host address の違いを理解するために、ネットワークの基本概念から説明します。

🔹 host address (127.0.0.1 や 192.168.3.8)
127.0.0.1 (ループバックアドレス)：

ローカルマシンのみ で通信するためのアドレス。
他のPCやデバイスからはアクセスできない。
127.0.0.2, 127.0.0.3 なども同じローカルループバックネットワーク内。
192.168.3.8 (ローカルネットワークIP)：

ルーターを介して LAN 内の他のPCからアクセス可能 なアドレス。
192.168.x.x はプライベートIPアドレスの範囲で、外部インターネットからは直接アクセスできない。
➡ つまり、host address は immudb が「どのネットワークインターフェースで通信を受け付けるか」を決める設定。

🔹 --immudb-address (198.167.3.8 のような外部IP)
--immudb-address は クライアント (immuadmin, immuclient) がどの immudb インスタンスに接続するか を指定するオプション。

--immudb-address 127.0.0.1：
ローカルマシン上の immudb に接続する。
immudb が 127.0.0.1 で動作していれば、この設定で接続可能。

--immudb-address 192.168.3.8：
同じ LAN 内の 192.168.3.8 で動作する immudb に接続する。
immudb が 192.168.3.8 で動作していれば、LAN 内の他のマシンからも接続可能。

--immudb-address 198.167.3.8：
これはグローバルIPアドレスの例。
外部インターネットに公開されている immudb に接続する場合 に使用。
ただし、ファイアウォールやルーターのポートフォワーディングが必要。
➡ つまり、--immudb-address は「どこに接続するか」を指定するオプション。

🔹 具体的な immuadmin の実行例
powershell
Copy
Edit
D:\immuDB\immuadmin.exe user permission immudb defaultdb RW --immudb-address 192.168.3.8 --immudb-port 3322
このコマンドの意味：

immuadmin.exe user permission：ユーザーの権限を設定する。
immudb：対象のユーザー名。
defaultdb：データベース名。
RW：読み書き (Read & Write) 権限を付与。
--immudb-address 192.168.3.8：
192.168.3.8 の immudb に接続して、設定を適用する。
--immudb-port 3322：
ポート 3322 で動作している immudb に接続する。
➡ この設定が正しい場合、192.168.3.8 で動作する immudb に対して RW 権限が付与される。

💡 127.0.0.1 と 127.0.0.2 の競合問題
127.0.0.1 で asia が動いている場合、同じ 127.0.0.1 で europe を立ち上げようとするとポートが衝突する可能性がある。

解決策：
異なる host address を使用する
asia：127.0.0.1
europe：127.0.0.2
northamerica：127.0.0.3
southamerica：127.0.0.4
異なる port を使用する

asia：3323
europe：3324
northamerica：3327
southamerica：3328

例：
immudb.exe --config immudb_asia.toml --address 127.0.0.1 --port 3323
immudb.exe --config immudb_europe.toml --address 127.0.0.2 --port 3324
immudb.exe --config immudb_northamerica.toml --address 127.0.0.3 --port 3327
immudb.exe --config immudb_southamerica.toml --address 127.0.0.4 --port 3328
➡ これなら競合しない！

🔹 まとめ
項目	役割
host address	immudb がどのネットワークインターフェースで動作するか
--immudb-address	クライアントが接続する immudb のアドレス
127.0.0.1	 ローカルマシン専用、外部アクセス不可
192.168.x.x  	LAN 内の他のPCからアクセス可能
198.x.x.x	 グローバルIP（外部アクセス）
--port	  immudb が待ち受けるポート番号
✅ immudb を複数立ち上げるなら、host address か port を変えれば競合しない！ 🚀


# metrics-address = "192.168.3.8:9497/metrics" の意味
metrics-address は、Prometheus などの監視ツールが immudb のメトリクスを取得するためのエンドポイントを指定する設定。

📌 基本構成
metrics-address = "192.168.3.8:9497/metrics"
これは、「メトリクスデータを 192.168.3.8 の 9497 ポートで公開する」 という意味。

🔹 metrics-address の役割
metrics-address を設定すると、immudb は指定したアドレスでメトリクスデータを公開し、監視ツールがこのデータを取得できるようになります。
metrics-address = "0.0.0.0:9497/metrics"

すべてのインターフェースでメトリクスを公開する（ローカルPC・LAN内の他のPC・外部PC など）
外部からもメトリクスを取得できるので セキュリティリスク あり
metrics-address = "127.0.0.1:9497/metrics"

ローカルPC のみがアクセス可能
他のPCやサーバーからメトリクスを取得することはできない
metrics-address = "192.168.3.8:9497/metrics"

LAN 内の他のPC からメトリクスを取得できる
Prometheus などの監視ツールが 192.168.3.8:9497/metrics にアクセス可能

🔹 metrics-address の /metrics とは？
/metrics は HTTPエンドポイント の一部であり、アクセスすると JSON や Prometheus 形式のデータ を取得できる。
例:
curl http://192.168.3.8:9497/metrics
→ immudb の状態やリクエスト数、エラー数などの統計情報が返ってくる。

🔹 metrics-address の競合を避けるには？
複数の immudb インスタンスを立ち上げる場合、同じ metrics-address だと競合する可能性がある。

✅ 対策: 各インスタンスごとに異なるポートを指定する
/ Asia の immudb 設定
metrics-address = "192.168.3.8:9498/metrics"

/ Europe の immudb 設定
metrics-address = "192.168.3.8:9499/metrics"

/ North America の immudb 設定
metrics-address = "192.168.3.8:9502/metrics"

/ South America の immudb 設定
metrics-address = "192.168.3.8:9503/metrics"
➡ これで、各大陸の immudb が異なるメトリクスポートで動作するため、競合しない！ 🚀

🔹 まとめ
設定値	説明
0.0.0.0:9497/metrics	すべてのインターフェースでメトリクス公開（外部からのアクセス可能）
127.0.0.1:9497/metrics	ローカルPCのみアクセス可能（安全）
192.168.3.8:9497/metrics	LAN 内の他のPCからアクセス可能（複数のインスタンスで競合の可能性あり）
192.168.3.8:9497, 9498, 9499, 9500	各インスタンスごとに異なるポートを指定して競合を防ぐ
✅ metrics-address は、複数の immudb を動かす場合は競合しないようにポートを変えることが重要！ 🚀