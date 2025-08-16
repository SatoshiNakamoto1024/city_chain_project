# ベースイメージとして最新のRustを使用
FROM rust:latest

# 作業ディレクトリを設定
WORKDIR /usr/src/app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    python3 \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
RUN pip3 install --no-cache-dir flask pyntru

# NTRUクレートの依存関係をビルド
COPY ../ntru /usr/src/app/ntru
RUN cd /usr/src/app/ntru && cargo build --release

# immudb_protoクレートをビルド
COPY ../immudb_proto /usr/src/app/immudb_proto
RUN cd /usr/src/app/immudb_proto && cargo build --release

# ソースコードをコピー
COPY . .

# メインアプリケーションをビルド
RUN cargo build --release

# Flaskのポートや環境変数を設定
ENV FLASK_PORT=5000

# Rustアプリケーションを起動するコマンド
CMD ["./target/release/municipal_chain"]
