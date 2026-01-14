# バックエンド用のDockerfile
FROM python:3.13-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
# PostgreSQLクライアントライブラリに必要
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# バックエンドの依存関係をコピー（本番用 + テスト用）
COPY backend/requirements.txt backend/requirements-test.txt ./

# Pythonパッケージをインストール（アプリ本体 + pytest などのテスト用依存）
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-test.txt

# バックエンドのコードをコピー
COPY backend/ .

# ポート8000を公開。イメージ利用者に伝えるための情報 (強制しない)。
EXPOSE 8000

# アプリケーションを起動
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
