# Dockerfile
FROM python:3.12-slim

# 作業ディレクトリを login_app に設定
WORKDIR /app

# 必要なシステム依存パッケージのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    libz-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt をコピー（login_app内に置くか、プロジェクトルートから参照するか検討）
COPY requirements.txt ./

# Python パッケージをインストール
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# プロジェクト全体（または login_app のコード）をコピー
COPY . .

# Expose ポート（login_app は5000番ポートを使っているので）
EXPOSE 5000

# コンテナ起動時のコマンド: login_app のエントリーポイント
CMD ["python", "app_login.py"]
