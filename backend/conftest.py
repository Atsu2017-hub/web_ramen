"""
pytest設定ファイル
テスト用のフィクスチャと設定を定義
"""
import pytest
import os
import sys
from typing import Generator
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv  

# .envファイルから環境変数を読み込む
load_dotenv()

# abspath: このファイルの絶対パスを取得
# dirname: このファイルが入っているディレクトリ名を取得
# insert: sys.pathにimportで探しに行くフォルダがあり、その0番目にパスを追加
# 結果的に
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# テスト用データベース設定（環境変数で上書き可能）
TEST_DB_CONFIG = {
    "DB_HOST": os.getenv("TEST_DB_HOST", "localhost"),
    "DB_PORT": os.getenv("TEST_DB_PORT", "5432"),
    "DB_NAME": os.getenv("TEST_DB_NAME", "ramen_restaurant_test"),
    "DB_USER": os.getenv("TEST_DB_USER", "postgres"),
    "DB_PASSWORD": os.getenv("TEST_DB_PASSWORD", "postgres"),
}

# fixture: 「テストを実行するための『お膳立て』をしてくれる関数」
# 例えば、データベース接続、ログイン済みクライアントの用意など。
# これらを共通化して、必要なテストにだけ提供する仕組み


# テスト用環境変数を設定
# scope: session (テスト全体の開始から終了までの間)
# sessionのほかにmodule(ファイルごと), class(クラスごと), function(関数ごと)の範囲がある。
# autouse: このフィクスチャは自動的に実行される。
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """テストセッション開始時に環境変数を設定"""
    # テスト用データベース設定を適用
    for key, value in TEST_DB_CONFIG.items():
        os.environ[key] = value
    
    # テスト用のシークレットキー
    if "SECRET_KEY" not in os.environ:
        os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    
    # Stripe、OpenAI、Slackのモック用設定
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_mock"
    os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_mock"
    os.environ["OPENAI_API_KEY"] = "sk-test-mock"
    os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/test/mock"
    
    yield # ここでテスト本体へバトンタッチ

    # 後処理。全テストが終わった後に実行される
    # テスト終了後のクリーンアップ（必要に応じて）

# fixtureの引数がない時はデフォルトのscopeがfunction, autouseがFalse (テスト関数でmock_stripeと指定して実行される)。
# patch関数でテストの間だけオブジェクトをモックにすり替える。withを抜けると元に戻る。
@pytest.fixture
def mock_stripe():
    """Stripe APIのモック"""
    with patch('server.stripe') as mock:
        # Payment Intentのモック
        mock_payment_intent = MagicMock() # どんなメソッドを読んでもエラーにならず指定した値を返すテスト用オブジェクト
        mock_payment_intent.id = "pi_test_123"
        mock_payment_intent.client_secret = "pi_test_123_secret_test"
        mock_payment_intent.status = "succeeded"
        mock_payment_intent.amount = 1000
        mock_payment_intent.latest_charge = "ch_test_123"
        
        # 指定していないメソッドを呼ぶとエラーにはならず、新しいMagicMockオブジェクトが返ってくる。
        mock.PaymentIntent.create.return_value = mock_payment_intent
        mock.PaymentIntent.retrieve.return_value = mock_payment_intent
        
        # Refundのモック
        mock_refund = MagicMock()
        mock_refund.id = "re_test_123"
        mock_refund.amount = 1000
        mock_refund.status = "succeeded"
        mock.Refund.create.return_value = mock_refund
        
        yield mock


@pytest.fixture
def mock_openai():
    """OpenAI APIのモック"""
    with patch('server.openai') as mock:
        mock_session = MagicMock()
        mock_session.client_secret = "session_test_secret"
        mock.beta.chatkit.sessions.create.return_value = mock_session
        yield mock


@pytest.fixture
def mock_slack():
    """Slack通知のモック"""
    with patch('slack_notification.send_slack_notification') as mock:
        mock.return_value = True
        yield mock

# TestClient: FastAPIのテスト用クライアント。appを渡すと、APIリクエストを送信できる。偽ブラウザ。サーバを立てすにテストできる (高速)
# returnは値をテスト関数に渡しその時点で終了。後片づけなし。
@pytest.fixture
def client(mock_stripe, mock_openai, mock_slack): # 引数にfixtureを渡すと、順に呼び出される
    """テスト用のFastAPIクライアント"""
    # モックを適用してからサーバーをインポート
    from server import app
    return TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """テスト用データベースのセットアップとクリーンアップ"""
    from database import get_db_connection, get_db_cursor
    import psycopg2
    
    # 環境変数を一時的に上書き
    original_env = {}
    for key, value in TEST_DB_CONFIG.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    # テスト用データベースに接続
    conn = None
    try:
        conn = psycopg2.connect(**{
            "host": TEST_DB_CONFIG["DB_HOST"],
            "port": int(TEST_DB_CONFIG["DB_PORT"]),
            "database": TEST_DB_CONFIG["DB_NAME"],
            "user": TEST_DB_CONFIG["DB_USER"],
            "password": TEST_DB_CONFIG["DB_PASSWORD"],
        })
        
        # テスト用テーブルを作成
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menus (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price INTEGER NOT NULL CHECK (price >= 0),
                image_url VARCHAR(500),
                is_available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reservation_date DATE NOT NULL,
                reservation_time TIME NOT NULL,
                number_of_people INTEGER NOT NULL CHECK (number_of_people > 0),
                special_requests TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                payment_intent_id VARCHAR(255),
                amount INTEGER,
                payment_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservation_menu_items (
                id SERIAL PRIMARY KEY,
                reservation_id INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
                menu_id INTEGER NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(reservation_id, menu_id)
            )
        """)
        conn.commit()
        
        yield conn
        
    finally:
        # テストデータをクリーンアップ
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("TRUNCATE TABLE reservation_menu_items CASCADE")
                cursor.execute("TRUNCATE TABLE reservations CASCADE")
                cursor.execute("TRUNCATE TABLE menus CASCADE")
                cursor.execute("TRUNCATE TABLE users CASCADE")
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"クリーンアップエラー: {e}")
            finally:
                cursor.close()
                conn.close()
        
        # 環境変数を元に戻す
        try:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        except:
            pass  # original_envが定義されていない場合は何もしない


@pytest.fixture
def test_user(client, test_db):
    """テスト用ユーザーを作成"""
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "テストユーザー"
    }
    
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    
    return {
        **user_data,
        "id": data["user"]["id"],
        "token": data["access_token"]
    }


@pytest.fixture
def test_menu(test_db):
    """テスト用メニューを作成"""
    from database import get_db_connection, get_db_cursor
    
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        cursor.execute("""
            INSERT INTO menus (name, description, price, image_url, is_available)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, description, price, image_url, is_available
        """, ("テストラーメン", "テスト用ラーメン", 850, "test.png", True))
        
        menu = cursor.fetchone()
        conn.commit()
        
        return dict(menu)
    finally:
        cursor.close()
        conn.close()

