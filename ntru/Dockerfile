# ベースイメージとして公式のRustランタイムを使用
FROM rust:latest

# 作業ディレクトリを設定
WORKDIR /usr/src/ntru

# 必要なファイルをコピー
COPY Cargo.toml Cargo.lock ./

# 依存関係をダウンロードしてビルドキャッシュを利用可能に
RUN cargo fetch

# ソースコードをコピー
COPY src ./src

# プロジェクトをリリースビルド
RUN cargo build --release

# 実行ファイルのパスを環境変数に追加
ENV PATH="/usr/src/ntru/target/release:${PATH}"

# コンテナの不要なキャッシュを削除して軽量化
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# デフォルトの実行コマンド
CMD ["./target/release/ntru_example"]
