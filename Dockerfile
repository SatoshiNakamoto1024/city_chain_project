FROM rust:latest

# 作業ディレクトリを設定
WORKDIR /usr/src/app

# ソースコードをコピー
COPY . .

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y pkg-config libssl-dev python3 python3-pip

# Pythonの依存関係をインストール
RUN pip3 install flask pyntru

# NTRUクレートの依存関係をビルド
COPY ../ntru /usr/src/app/ntru
RUN cd /usr/src/app/ntru && cargo build --release

# メインアプリケーションをビルド
RUN cargo build --release

# アプリケーションを起動
CMD ["./target/release/municipal_chain"]
