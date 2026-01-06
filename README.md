# 🍜 本格ラーメン屋 - Webサイト

本格ラーメン屋の予約・注文システムを構築したWebアプリケーションです。ユーザー認証、予約管理、Stripe決済、AIチャット機能を統合したフルスタックアプリケーションです。

## 📋 目次

- [主な機能](#主な機能)
- [技術スタック](#技術スタック)
- [プロジェクト構造](#プロジェクト構造)
- [セットアップ方法](#セットアップ方法)
- [環境変数の設定](#環境変数の設定)
- [使用方法](#使用方法)
- [APIエンドポイント](#apiエンドポイント)

## ✨ 主な機能

### フロントエンド機能
- **レスポンシブデザイン**: モバイル・タブレット・デスクトップに対応
- **メニュー表示**: ラーメン、丼、サイドメニューなどのメニュー一覧表示
- **ユーザー認証**: 新規登録・ログイン機能（JWT認証）
- **予約システム**: 日時・人数・メニュー選択による予約機能
- **決済機能**: Stripeによる安全なオンライン決済
- **AIチャット**: OpenAI ChatKitによる自動応答チャット機能
- **予約管理**: 予約一覧の表示・キャンセル機能

### バックエンド機能
- **RESTful API**: FastAPIによるAPIサーバー
- **認証・認可**: JWTトークンによるセキュアな認証
- **データベース管理**: PostgreSQLによるデータ永続化
- **決済処理**: Stripe APIによる決済・返金処理
- **通知機能**: Slackへの予約通知（予約確定・キャンセル）

## 🛠 技術スタック

### フロントエンド
- **HTML5**: セマンティックなマークアップ
- **CSS3**: モダンなスタイリング、レスポンシブデザイン
- **JavaScript (ES6+)**: バニラJSによるインタラクティブな機能実装
- **Stripe.js**: 決済フォームの統合
- **OpenAI ChatKit**: AIチャット機能

### バックエンド
- **Python 3.x**: サーバーサイド言語
- **FastAPI**: モダンなWebフレームワーク
- **PostgreSQL**: リレーショナルデータベース
- **JWT**: トークンベース認証
- **Stripe API**: 決済処理
- **OpenAI API**: ChatKitセッション管理
- **Slack API**: 通知機能

### 開発ツール
- **psycopg2**: PostgreSQL接続ライブラリ
- **python-dotenv**: 環境変数管理
- **uvicorn**: ASGIサーバー

## 📁 プロジェクト構造

```
web_ramen/
├── backend/                 # バックエンド（FastAPI）
│   ├── server.py           # メインサーバーファイル
│   ├── auth.py             # 認証機能
│   ├── database.py         # データベース接続・管理
│   ├── init_db.py          # データベース初期化
│   ├── slack_notification.py # Slack通知機能
│   └── requirements.txt    # Python依存パッケージ
├── src/                    # フロントエンドJavaScriptモジュール
│   ├── auth.js             # 認証API呼び出し
│   ├── auth-ui.js          # 認証UI制御
│   ├── menu.js             # メニュー管理
│   ├── reservation.js      # 予約API呼び出し
│   ├── reservation-ui.js   # 予約UI制御
│   └── chatkit.js          # ChatKit統合
├── 画像/                   # 画像リソース
│   ├── ramen.png
│   ├── don.png
│   ├── karaage.png
│   └── cola.png
├── index.html              # メインHTMLファイル
├── style.css               # スタイルシート
├── script.js               # メインJavaScriptファイル
└── README.md               # このファイル
```

## 🚀 セットアップ方法

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd web_ramen
```

### 2. バックエンドのセットアップ

#### 2.1 Python環境の準備

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

#### 2.2 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

#### 2.3 PostgreSQLデータベースのセットアップ

PostgreSQLをインストールし、データベースを作成します。

```sql
CREATE DATABASE ramen_restaurant;
```

#### 2.4 データベースの初期化

```bash
python init_db.py
```

### 3. フロントエンドのセットアップ

フロントエンドは静的ファイルのため、特別なビルドプロセスは不要です。Webサーバーで配信するか、直接HTMLファイルを開いて使用できます。

開発環境では、CORS設定によりバックエンドAPIと通信できます。

## 🔐 環境変数の設定

バックエンドディレクトリに `.env` ファイルを作成し、以下の環境変数を設定してください。

```env
# データベース設定
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ramen_restaurant
DB_USER=postgres
DB_PASSWORD=your_password

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

### 環境変数の取得方法

1. **Stripe APIキー**: [Stripe Dashboard](https://dashboard.stripe.com/apikeys) から取得
2. **OpenAI APIキー**: [OpenAI Platform](https://platform.openai.com/api-keys) から取得
3. **Slack Webhook URL**: SlackワークスペースでIncoming Webhookを設定して取得

## 📖 使用方法

### バックエンドサーバーの起動

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

サーバーは `http://localhost:8000` で起動します。

### フロントエンドの起動

#### 方法1: ローカルWebサーバーを使用（推奨）

```bash
# Python 3の場合
python -m http.server 8080

# Node.jsの場合
npx http-server -p 8080
```

ブラウザで `http://localhost:8080` にアクセスします。

#### 方法2: 直接ファイルを開く

`index.html` をブラウザで直接開くことも可能ですが、CORS制限により一部機能が制限される場合があります。

### アプリケーションの使用フロー

1. **メニュー閲覧**: ホームページからメニューを確認
2. **ユーザー登録**: 「予約」セクションから新規登録
3. **ログイン**: 登録したアカウントでログイン
4. **予約作成**: 日時・人数・メニューを選択して予約
5. **決済**: Stripeで安全に決済
6. **予約確認**: 予約一覧で確認・キャンセルが可能
7. **チャット**: AIチャットで質問・相談

## 🔌 APIエンドポイント

### 認証関連

- `POST /api/auth/register` - ユーザー新規登録
- `POST /api/auth/login` - ログイン
- `GET /api/auth/me` - 現在のユーザー情報取得（認証必要）

### メニュー関連

- `GET /api/menus` - メニュー一覧取得

### 予約関連

- `POST /api/reservations` - 予約作成（認証必要）
- `GET /api/reservations` - 予約一覧取得（認証必要）
- `DELETE /api/reservations/{id}` - 予約キャンセル（認証必要）

### 決済関連

- `GET /api/stripe/publishable-key` - Stripe公開キー取得
- `POST /api/payments/create-intent` - Payment Intent作成（認証必要）
- `POST /api/payments/refund/{payment_intent_id}` - 返金処理（認証必要）

### ChatKit関連

- `POST /api/chatkit/session` - ChatKitセッション作成
- `POST /api/widget-action` - ChatKitウィジェットアクション処理

## 📝 データベーススキーマ

### users テーブル
- `id`: 主キー（自動増分）
- `email`: メールアドレス（ユニーク）
- `password_hash`: パスワードハッシュ
- `name`: ユーザー名
- `created_at`: 作成日時

### menus テーブル
- `id`: 主キー（自動増分）
- `name`: メニュー名
- `description`: 説明
- `price`: 価格
- `image_url`: 画像URL
- `is_available`: 利用可能フラグ

### reservations テーブル
- `id`: 主キー（自動増分）
- `user_id`: ユーザーID（外部キー）
- `reservation_date`: 予約日
- `reservation_time`: 予約時間
- `number_of_people`: 人数
- `special_requests`: 特別な要望
- `status`: 予約ステータス
- `payment_intent_id`: Stripe Payment Intent ID
- `amount`: 決済金額
- `payment_status`: 決済ステータス
- `created_at`: 作成日時

### reservation_menu_items テーブル
- `id`: 主キー（自動増分）
- `reservation_id`: 予約ID（外部キー）
- `menu_id`: メニューID（外部キー）
- `quantity`: 数量

## 🔒 セキュリティ機能

- **パスワードハッシュ化**: bcryptによる安全なパスワード保存
- **JWT認証**: トークンベースの認証システム
- **CORS設定**: 適切なCORS設定によるセキュリティ
- **環境変数管理**: 機密情報の安全な管理
- **Stripe決済**: PCI準拠の安全な決済処理

## 🎨 UI/UXの特徴

- **モダンなデザイン**: 洗練されたUIデザイン
- **レスポンシブ対応**: あらゆるデバイスで快適に使用可能
- **スムーズなアニメーション**: ユーザー体験を向上させるアニメーション
- **直感的な操作**: 分かりやすいナビゲーションとフォーム

## 📄 ライセンス

このプロジェクトは個人開発の練習用プロジェクトです。

## 👤 作成者

個人開発練習プロジェクト

## 🙏 謝辞

- [FastAPI](https://fastapi.tiangolo.com/)
- [Stripe](https://stripe.com/)
- [OpenAI](https://openai.com/)
- [PostgreSQL](https://www.postgresql.org/)

---

**注意**: 本番環境で使用する場合は、環境変数の適切な設定、セキュリティ対策、エラーハンドリングの強化などが必要です。

