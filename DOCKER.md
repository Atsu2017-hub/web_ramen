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

#### 開発環境

プロジェクトルートで以下のコマンドを実行：

```bash
# コンテナをビルドして起動（開発環境用）
docker-compose up -d --build
```

初回起動時は、イメージのビルドとデータベースの初期化に時間がかかります。

**開発環境の特徴:**
- コードの変更が自動的に反映される（volumes マウント）
- ホットリロードが有効（`--reload` オプション）
- 開発に適した設定

#### 本番環境

```bash
# 1. 静的ファイルをビルド（dist/ ディレクトリに出力）
npm run build

# 2. 本番環境用のコンテナをビルドして起動
docker-compose -f docker-compose.prod.yml up -d --build
```

**本番環境の特徴:**
- コードはイメージに含まれる（volumes を使用しない）
- 静的ファイルは `dist/` ディレクトリにビルドしてからマウント
- ホットリロードは無効（パフォーマンス重視）
- 自動再起動設定（`restart: unless-stopped`）
- 本番用のネットワーク・ボリューム名を使用

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

# pytestを実行（バックエンドテスト）
docker-compose exec backend pytest
```

### フロントエンドテストの実行

フロントエンドテストは、一時的な Node.js コンテナで実行します：

```bash
# Vitestを実行（1回だけ実行、watchなし）
docker run --rm -v ${PWD}:/app -w /app -v /app/node_modules node:20 sh -c "npm install && npm run test:run"

# 通常の test（watchモード）を使う場合
docker run --rm -v ${PWD}:/app -w /app -v /app/node_modules node:20 sh -c "npm install && npm test"

# カバレッジ付きで実行
docker run --rm -v ${PWD}:/app -w /app -v /app/node_modules node:20 sh -c "npm install && npm run test:coverage"
```

**Windows PowerShell の場合**:
```powershell
# Vitestを実行（1回だけ実行、watchなし）
docker run --rm -v ${PWD}:/app -w /app -v /app/node_modules node:20 sh -c "npm install && npm run test:run"
```

**注意**: 
- `--rm` オプションにより、実行後にコンテナが自動的に削除されます
- `-v /app/node_modules` により、ローカルの `node_modules` を除外し、コンテナ内で Linux 用のバイナリをインストールします

### データベースに接続

```bash
# PostgreSQLに接続
docker-compose exec db psql -U postgres -d ramen_restaurant
```

## 📁 構成

### ファイル構成

- **docker-compose.yml**: 開発環境用（volumes でコードをマウント、ホットリロード有効）
- **docker-compose.prod.yml**: 本番環境用（volumes なし、コードはイメージに含まれる）

### サービス

- **db**: PostgreSQL 15データベース
- **backend**: FastAPIバックエンド（Python 3.13）
- **frontend**: Nginxによる静的ファイル配信

**注意**: フロントエンドテストは、一時的な Node.js コンテナ（`docker run`）で実行します。

### 開発環境と本番環境の違い

| 項目 | 開発環境 | 本番環境 |
|------|---------|---------|
| ファイル | `docker-compose.yml` | `docker-compose.prod.yml` |
| コードマウント | volumes でマウント | イメージに含まれる |
| ホットリロード | 有効（`--reload`） | 無効 |
| 自動再起動 | なし | `restart: unless-stopped` |
| ネットワーク名 | `ramen_network` | `ramen_network_prod` |
| ボリューム名 | `postgres_data` | `postgres_data_prod` |

### ネットワーク

- **開発環境**: `ramen_network`
- **本番環境**: `ramen_network_prod`

各環境で独立したネットワークを使用することで、開発環境と本番環境を分離できます。

### ボリューム

- **開発環境**: `postgres_data` - PostgreSQLのデータ永続化用
- **本番環境**: `postgres_data_prod` - PostgreSQLのデータ永続化用（開発環境とは別）

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

## 🚀 本番環境での使用

### 本番環境の起動

```bash
# 1. 静的ファイルをビルド（dist/ ディレクトリに出力）
npm run build

# 2. 本番環境用のコンテナを起動
docker-compose -f docker-compose.prod.yml up -d --build

# ログの確認
docker-compose -f docker-compose.prod.yml logs -f

# コンテナの停止
docker-compose -f docker-compose.prod.yml down

# データベースのデータも削除する場合
docker-compose -f docker-compose.prod.yml down -v
```

**ビルドコマンドのオプション:**
```bash
# クリーンビルド（既存の dist/ を削除してからビルド）
npm run build:clean

# 通常のビルド
npm run build
```

### 本番環境の特徴

1. **コードはイメージに含まれる**
   - volumes を使用しないため、コードの変更はイメージの再ビルドが必要
   - デプロイ時は `docker-compose -f docker-compose.prod.yml up -d --build` を実行

2. **ホットリロードは無効**
   - `--reload` オプションを削除してパフォーマンスを最適化

3. **自動再起動**
   - `restart: unless-stopped` により、コンテナが停止した場合に自動的に再起動

4. **環境変数の管理**
   - `.env.prod` ファイルを作成して本番環境用の環境変数を設定
   - または、環境変数を直接指定

### 本番環境での静的ファイルの配布

本番環境では、`npm run build` コマンドで静的ファイルを `dist/` ディレクトリにビルドし、そのディレクトリをNginxコンテナにマウントします。

**ビルドプロセス:**
1. `npm run build` を実行
2. 必要な静的ファイル（`index.html`、`style.css`、`script.js`、`src/`、`画像/`）が `dist/` にコピーされる
3. `docker-compose.prod.yml` で `dist/` を `/usr/share/nginx/html` にマウント

**ビルドされるファイル:**
- `index.html` - メインHTMLファイル
- `style.css` - スタイルシート
- `script.js` - メインJavaScriptファイル
- `src/` - JavaScriptモジュール
- `画像/` - 画像リソース

**注意:** `dist/` ディレクトリは `.gitignore` に含まれているため、Gitにはコミットされません。デプロイ前に必ず `npm run build` を実行してください。

## 📝 注意事項

- 本番環境で使用する場合は、`.env`ファイルの機密情報を適切に管理してください
- セキュリティのため、本番環境ではnginxの設定を適切に調整してください
- データベースのパスワードは強力なものに変更してください
- 本番環境では、環境変数を適切に設定してください（`.env.prod` ファイルの使用を推奨）