# PostgreSQLデータベース接続とテーブル管理用のモジュール
# psycopg2を使用してPostgreSQLに接続

import psycopg2  # PostgreSQL接続用ライブラリ
from psycopg2.extras import RealDictCursor  # 結果を辞書形式で取得するためのカーソル
import os  # 環境変数の取得に使用
from dotenv import load_dotenv  # .envファイルから環境変数を読み込む

# .envファイルから環境変数を読み込む
load_dotenv()

# データベース接続情報を環境変数から取得
# 環境変数が設定されていない場合はデフォルト値を使用
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),  # データベースホスト（デフォルト: localhost）
    "port": os.getenv("DB_PORT", "5432"),  # データベースポート（デフォルト: 5432）
    "database": os.getenv("DB_NAME", "ramen_restaurant"),  # データベース名（デフォルト: ramen_restaurant）
    "user": os.getenv("DB_USER", "postgres"),  # データベースユーザー名（デフォルト: postgres）
    "password": os.getenv("DB_PASSWORD", "postgres"),  # データベースパスワード（デフォルト: postgres）
}


def get_db_connection():
    """
    データベースへの接続を取得する関数
    
    Returns:
        psycopg2.connection: PostgreSQLデータベース接続オブジェクト
    """
    try:
        # PostgreSQLに接続
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        # 接続エラーが発生した場合、エラーメッセージを出力
        print(f"データベース接続エラー: {e}")
        raise


def init_database():
    """
    データベースのテーブルを初期化する関数
    ユーザーテーブルと予約テーブルを作成
    """
    conn = get_db_connection()
    cursor = conn.cursor() # タプル形式のカーソル
    
    try:
        # ユーザーテーブルの作成
        # id: 主キー（自動増分）
        # email: メールアドレス（一意制約付き）
        # password_hash: パスワードのハッシュ値（セキュリティのため平文で保存しない）
        # name: ユーザー名
        # created_at: アカウント作成日時
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 予約テーブルの作成
        # id: 主キー（SERIAL: 自動増分）
        # user_id: ユーザーID（外部キー、usersテーブルを参照）
        # reservation_date: 予約日
        # reservation_time: 予約時間
        # number_of_people: 人数
        # special_requests: 特別な要望（任意）
        # status: 予約ステータス（pending: 保留中、confirmed: 確認済み、cancelled: キャンセル）
        # created_at: 予約作成日時
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reservation_date DATE NOT NULL,
                reservation_time TIME NOT NULL,
                number_of_people INTEGER NOT NULL CHECK (number_of_people > 0),
                special_requests TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 変更をコミット（データベースに反映）
        conn.commit()
        print("データベーステーブルの初期化が完了しました")
    except psycopg2.Error as e:
        # エラーが発生した場合、ロールバック（変更を取り消し）
        conn.rollback()
        print(f"データベース初期化エラー: {e}")
        raise
    finally:
        # カーソルと接続を閉じる
        cursor.close()
        conn.close()


def get_db_cursor(conn):
    """
    辞書形式で結果を取得できるカーソルを返す関数
    
    Args:
        conn: データベース接続オブジェクト
    
    Returns:
        RealDictCursor: 辞書形式のカーソル
    """
    return conn.cursor(cursor_factory=RealDictCursor)

