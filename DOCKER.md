# Docker環境の使用方法

このプロジェクトをDockerで実行するための手順です。

## 📋 前提条件

- Docker Desktop（Windows/Mac）またはDocker Engine + Docker Compose（Linux）がインストールされていること

## 🚀 セットアップ手順

### 1. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、以下の環境変数を設定してください：

```env
# データベース設定
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ramen_restaurant
DB_USER=postgres
DB_PASSWORD=postgres

# JWT認証設定
SECRET_KEY=your-secret-key-change-in-production

# Stripe設定
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key

# OpenAI設定
OPENAI_API_KEY=sk-your-openai-api-key

# Slack設定（オプション）
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
```

**注意**: `.env` ファイルはGitにコミットしないでください（`.gitignore`に含まれています）。

### 2. Dockerコンテナの起動

プロジェクトルートで以下のコマンドを実行：

```bash
# コンテナをビルドして起動
docker-compose up -d --build
```

初回起動時は、イメージのビルドとデータベースの初期化に時間がかかります。

### 3. サービスの確認

以下のサービスが起動します：

- **フロントエンド**: http://localhost:8080
- **バックエンドAPI**: http://localhost:8000
- **PostgreSQL**: localhost:5432

### 4. ログの確認

```bash
# すべてのサービスのログを確認
docker-compose logs -f

# 特定のサービスのログを確認
docker-compose logs -f backend
docker-compose logs -f db
docker-compose logs -f frontend
```

### 5. コンテナの停止

```bash
# コンテナを停止
docker-compose down

# データベースのデータも削除する場合
docker-compose down -v
```

## 🔧 よくある操作

### データベースの再初期化

```bash
# コンテナを停止してボリュームを削除
docker-compose down -v

# 再度起動（データベースが初期化されます）
docker-compose up -d
```

### バックエンドのコード変更を反映

`docker-compose.yml`でボリュームマウントしているため、バックエンドのコードを変更すると自動的に反映されます（`--reload`オプションにより）。

フロントエンドの変更も、nginxの設定により自動的に反映されます。

### バックエンドコンテナ内でコマンドを実行

```bash
# バックエンドコンテナに入る
docker-compose exec backend sh

# データベース初期化スクリプトを実行
docker-compose exec backend python init_db.py

# pytestを実行
docker-compose exec backend pytest
```

### データベースに接続

```bash
# PostgreSQLに接続
docker-compose exec db psql -U postgres -d ramen_restaurant
```

## 📁 構成

### サービス

- **db**: PostgreSQL 15データベース
- **backend**: FastAPIバックエンド（Python 3.13）
- **frontend**: Nginxによる静的ファイル配信

### ネットワーク

すべてのサービスは `ramen_network` というDockerネットワークで接続されています。

### ボリューム

- `postgres_data`: PostgreSQLのデータ永続化用

## 🐛 トラブルシューティング

### ポートが既に使用されている場合

`.env`ファイルまたは`docker-compose.yml`でポート番号を変更してください。

### データベース接続エラー

バックエンドコンテナがデータベースの起動を待つように設定されていますが、エラーが発生する場合は：

```bash
# データベースのヘルスチェックを確認
docker-compose ps

# ログを確認
docker-compose logs db
docker-compose logs backend
```

### コンテナの再ビルド

コードの変更が反映されない場合：

```bash
# コンテナを再ビルド
docker-compose up -d --build
```

## 📝 注意事項

- 本番環境で使用する場合は、`.env`ファイルの機密情報を適切に管理してください
- セキュリティのため、本番環境ではnginxの設定を適切に調整してください
- データベースのパスワードは強力なものに変更してください
