あなたが実現したい構成はこうです:

Python 側が gRPC サーバーとして起動し、immuDB への読み書きを一括管理する。
Rust 側はクライアントとして Python gRPC サーバーにリクエストを送り、「データを保存したい」「データを読みたい」というときは常に Python サーバーを経由する。
これにより、Rust と immuDB の型不整合やメンテナンスの煩雑さを回避し、Python が immuDB を一元的に扱う。
以前のやり取りで「Rust 側では immuDB を操作しない」「あくまでも Python から immuDB へアクセスする設計」と言っていたのは、まさにこの構成です。
つまり 「パターンB: Python がサーバー、Rust はクライアント」 を選べば OK です。


immudbをrustで操作するには、
tonic を使って immudb と gRPC 経由で通信できます。
今後、gRPC .proto ファイルのビルド方法も調整する必要があるので、その手順も必要なら説明できます！

gRPC .proto ファイルのビルド方法
immudb と gRPC 経由で通信するためには、まず immudb の .proto ファイルを Rust コードに変換する必要があります。この手順を説明します。

1. 必要なクレートを Cargo.toml に追加
まず、Cargo.toml に tonic-build を追加します。

toml
[build-dependencies]
tonic-build = "0.6"
この tonic-build は .proto ファイルをコンパイルして、Rust の gRPC クライアントコードを生成するために使います。

2. build.rs の作成
プロジェクトのルートに build.rs を作成し、以下の内容を記述します。

build.rs
fn main() {
    tonic_build::configure()
        .build_server(false) // クライアントのみをビルド
        .compile(
            &["proto/schema.proto"], // ここに `immudb` の .proto ファイルのパスを指定
            &["proto"], // .proto ファイルのディレクトリ
        )
        .expect("Failed to compile protos");
}
この build.rs は、cargo build を実行すると .proto ファイルをコンパイルし、自動的に Rust コードを生成します。

3. .proto ファイルを取得
immudb の .proto ファイルを proto/ ディレクトリに配置します。

手動で取得する場合
immudb の .proto ファイルは、immudb GitHub から入手できます。

immudb の schema.proto をダウンロードします。
git clone https://github.com/codenotary/immudb.git

immudb/embedded/proto/schema.proto をプロジェクトの proto/ ディレクトリにコピー
cp immudb/embedded/proto/schema.proto D:\city_chain_project\network\DB\immudb\rs_immu\proto\


あなたの要望: Rust は immuDB を直接操作せず、「Python を gRPC サーバーとして経由し immuDB とやり取りする」
正解構成: Python = サーバー、Rust = クライアント
Rust 側で run_grpc_server は不要（サーバーは建てない）
Rust では ImmuDBClient のみ実装し、Python の gRPC サーバーに接続
今回提示したファイル構成はまさに「Rust がクライアントだけ実装する」形。
したがって「どっちなの？」への回答は、「Python がサーバー、Rust はクライアント」で合っています。
これで、「型が違う問題」を Python 側で集約し、Rust 側はシンプルなクライアント処理に専念できるようになります。

2. 実行手順
ターミナル (コマンドプロンプト/PowerShell など) を開き、Python 側のディレクトリへ移動
cd D:\city_chain_project\network\DB\py_immu

Python サーバーを起動
python py_immu_server.py
これで 0.0.0.0:50051 (または localhost:50051) で gRPC サーバーが待ち受け状態になる
（終了するには Ctrl + C）

別のターミナルを開き、Rust 側のディレクトリへ移動
cd D:\city_chain_project\network\DB\immudb\rs_immu
cargo run --bin main_immudb  で実行

Rust のクライアントが起動し、Python サーバーに対して Login, Set, Get などの RPC を呼び出す
Python のコンソール側にも「リクエストが来た」ログが表示されるはず

3. なぜ別フォルダなのか
Python サーバーは Python のライブラリ（grpcio, immudb Python SDK など）を使っているため、Rust の Cargo ビルドとは無関係にPython で動作します。Rust の cargo run はあくまで Rust バイナリをビルド & 実行するコマンドなので、Python スクリプトを自動的に起動することはありません。
したがって、Python のコードは Python 側のフォルダ (py_immu) に置き、Python で手動実行 → Rust クライアントは Rust 側 (rs_immu) で cargo run → それぞれ別のプロセスとして動きます。