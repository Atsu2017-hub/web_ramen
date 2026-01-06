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
        
        # メニューテーブルの作成
        # id: 主キー（SERIAL: 自動増分）
        # name: メニュー名
        # description: メニューの説明
        # price: 価格（整数、単位は円）
        # image_url: 画像URL（任意）
        # is_available: 利用可能かどうか（デフォルト: true）
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
        
        # 予約テーブルの作成（決済情報を追加）
        # id: 主キー（SERIAL: 自動増分）
        # user_id: ユーザーID（外部キー、usersテーブルを参照）
        # reservation_date: 予約日
        # reservation_time: 予約時間
        # number_of_people: 人数
        # special_requests: 特別な要望（任意）
        # status: 予約ステータス（pending: 保留中、confirmed: 確認済み、cancelled: キャンセル）
        # payment_intent_id: StripeのPayment Intent ID（決済識別子）
        # amount: 決済金額（整数、単位は円）
        # payment_status: 決済ステータス（pending: 未決済、succeeded: 決済完了、refunded: 返金済み）
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
                payment_intent_id VARCHAR(255),
                amount INTEGER,
                payment_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 予約メニュー関連テーブル（予約とメニューの多対多の関係）
        # reservation_id: 予約ID（外部キー）
        # menu_id: メニューID（外部キー）
        # quantity: 数量
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
        
        # メニューの初期データを挿入（既に存在する場合はスキップ）
        cursor.execute("SELECT COUNT(*) FROM menus")
        menu_count = cursor.fetchone()[0]
        
        if menu_count == 0:
            # メニュー初期データを挿入
            menus_data = [
                ("本格ラーメン", "長時間煮込んだ濃厚スープと、こだわりの麺が自慢の一杯。チャーシュー、味玉、ネギがたっぷりと盛り付けられています。", 850, "画像/ramen.png"),
                ("特製丼", "ボリューム満点の特製丼。ご飯の上にたっぷりの具材をのせた、満足感のある一品です。", 750, "画像/don.png"),
                ("特製唐揚げ", "ジューシーでサクサクの特製唐揚げ。秘伝のタレで味付けした、絶品サイドメニューです。", 550, "画像/karaage.png"),
                ("ドリンク", "コーラ、オレンジジュース、お茶など、各種ドリンクをご用意しています。", 200, "画像/cola.png"),
            ]
            
            cursor.executemany(
                "INSERT INTO menus (name, description, price, image_url) VALUES (%s, %s, %s, %s)",
                menus_data
            )
            print("メニューの初期データを挿入しました")
        
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

