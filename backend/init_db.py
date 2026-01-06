# データベースを手動で初期化するスクリプト (server.pyで自動で初期化されるため、通常は使用しない)
# このスクリプトを実行すると、usersテーブルとreservationsテーブルが作成されます

from database import init_database

if __name__ == "__main__":
    print("データベースを初期化しています...")
    try:
        init_database()
        print("データベースの初期化が完了しました！")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

