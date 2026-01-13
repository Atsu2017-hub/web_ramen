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
    "host": os.getenv("DB_HOST", "localhost"),  # データベースホスト（デフォルト: localhost）
    "port": os.getenv("DB_PORT", "5432"),  # データベースポート（デフォルト: 5432）
    "database": os.getenv("DB_NAME", "ramen_restaurant"),  # データベース名（デフォルト: ramen_restaurant）
    "user": os.getenv("DB_USER", "postgres"),  # データベースユーザー名（デフォルト: postgres）
    "password": os.getenv("DB_PASSWORD", "postgres"),  # データベースパスワード（デフォルト: postgres）
}

# テスト用環境変数を設定
# scope: session (テスト全体の開始から終了までの間)
# sessionのほかにmodule(ファイルごと), class(クラスごと), function(関数ごと)の範囲がある。
# autouse: このフィクスチャは自動的に実行される。
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():       
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
    from database import get_db_connection, get_db_cursor, init_database
    
    # データベースを初期化（テーブル作成とメニュー初期データの挿入）
    init_database()
    
    # テスト用データベースに接続
    conn = None
    try:
        conn = get_db_connection()
        
        yield conn
        
    finally:
        # テストデータをクリーンアップ
        if conn:
            cursor = get_db_cursor(conn)
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

