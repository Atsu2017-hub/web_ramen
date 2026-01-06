# FastAPIを使用。これでHTTPサーバを構築。
# OpenAIを使用。これでOpenAIのAPIを呼び出す。
# osを使用。これで環境変数を取得。
# dotenvを使用。これで.envファイルから環境変数を読み込む。

from fastapi import FastAPI, Request, Depends, HTTPException, status  # pyright: ignore[reportMissingImports]
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # pyright: ignore[reportMissingImports]
from openai import OpenAI  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, EmailStr  # pyright: ignore[reportMissingImports]
from typing import Any, Dict, Optional  # pyright: ignore[reportMissingImports]
from datetime import date, time  # pyright: ignore[reportMissingImports]
import os  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

# 認証とデータベース関連のモジュールをインポート
from auth import (
    authenticate_user, create_user, create_access_token, 
    verify_token, get_user_by_email
)  # pyright: ignore[reportMissingImports]
from database import get_db_connection, get_db_cursor, init_database  # pyright: ignore[reportMissingImports]
from slack_notification import (
    notify_reservation_confirmed, notify_reservation_cancelled
)  # pyright: ignore[reportMissingImports]

# .envファイルから環境変数を読み込む
load_dotenv()

# FastAPIのインスタンスを作成。
app = FastAPI()

# CORS設定（開発環境用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAIのインスタンスを作成。OpenAIのAPIキーを環境変数から取得。
openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# HTTPBearerを使用してJWTトークンの認証を行う
security = HTTPBearer()

# アプリケーション起動時にデータベースを初期化

# @app.on_event("startup")
# async def startup_event():
#     """アプリケーション起動時にデータベーステーブルを初期化"""
#     try:
#         init_database()
#     except Exception as e:
#         print(f"データベース初期化エラー: {e}")

# リクエストボディのモデル定義
class WidgetActionRequest(BaseModel):
    # 型検査は型変換して通す可能性あり。
    action: Dict[str, Any] # jsonのキーは文字列
    itemId: str

# ユーザー登録用のリクエストモデル
class UserRegister(BaseModel):
    email: EmailStr  # メールアドレス（バリデーション付き）
    password: str  # パスワード
    name: str  # ユーザー名

# ログイン用のリクエストモデル
class UserLogin(BaseModel):
    email: EmailStr  # メールアドレス
    password: str  # パスワード

# 予約作成用のリクエストモデル
class ReservationCreate(BaseModel):
    reservation_date: date  # 予約日
    reservation_time: str  # 予約時間（文字列形式、例: "18:00"）
    number_of_people: int  # 人数
    special_requests: Optional[str] = None  # 特別な要望（任意）

# 現在のユーザーを取得する依存関数。security(HttpBearerの返り値)を指定すると、Authorizarionヘッダーを見て、Bearer <token>の形式か判断し取り出す。
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    JWTトークンから現在のユーザー情報を取得する関数
    認証が必要なエンドポイントで使用
    
    Args:
        credentials: HTTPBearerから取得した認証情報
        credentials.scheme → "Bearer"
        credentials.credentials → トークン文字列(トークンのみ)
    
    Returns:
        dict: ユーザー情報
    
    Raises:
        HTTPException: トークンが無効な場合
    """
    # トークンを検証
    payload = verify_token(credentials.credentials)
    email = payload.get("sub")  # トークンに含まれるメールアドレス
    
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効な認証情報です"
        )
    
    # ユーザー情報を取得
    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません"
        )
    
    # パスワードハッシュを返さないようにする
    user.pop("password_hash", None)
    return user

# /api/chatkit/session にPOSTリクエストが来た時の処理。
@app.post("/api/chatkit/session")
def create_chatkit_session(): 
    session = openai.beta.chatkit.sessions.create(
      user="user",
      workflow={
        "id": "wf_695209dd2a188190a99acf5b73ee77d809b3b904f6ee188e"
      }
    )
    return { "client_secret": session.client_secret }

# /api/widget-action にPOSTリクエストが来た時の処理。
@app.post("/api/widget-action")
async def widget_action(request: WidgetActionRequest):
    """
    ChatKitのウィジェットアクションを処理
    
    ChatKitのwidgets.onActionから呼び出されるエンドポイント
    アクションタイプに応じて適切な処理を実行

    フロントからのjsonをpythonで受け取る方法
    1. BaseModelを使用してモデルを定義。33行目を実行してモデルを定義。
    2. FastAPIのRequestを使用してリクエストを受け取り、request.json()jsonを読み取ってpythonの型に変換。
    """
    action = request.action
    item_id = request.itemId
    action_type = action.get("type") 
    action_payload = action.get("payload") 
    
    # アクションタイプに応じた処理
    if action_type == "ramen.faq":
        # 例: アクションIDを取得して処理
        action_id = action_payload.get("id") if isinstance(action_payload, dict) else None
        response = await do_thing(action_id)
        
        print(response);
        return {"response":response}
    else:
        # その他のアクションタイプ
        return {"response":"NG"}

async def do_thing(action_id: Optional[str]):
    """
    アクション処理の実装例
    
    実際の処理をここに実装します：
    - データベースへの保存
    - 外部APIの呼び出し
    - ビジネスロジックの実行
    """
    return action_id

# ========== 認証関連のAPIエンドポイント ==========

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    """
    ユーザー登録エンドポイント
    
    新しいユーザーアカウントを作成します
    
    Args:
        user_data: ユーザー登録情報（メールアドレス、パスワード、名前）
    
    Returns:
        dict: 作成されたユーザー情報とアクセストークン
    """
    try:
        # ユーザーを作成
        user = create_user(user_data.email, user_data.password, user_data.name)
        
        # アクセストークンを生成
        access_token = create_access_token(data={"sub": user["email"]})
        
        return {
            "user": user,
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ユーザー登録に失敗しました: {str(e)}"
        )


@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    """
    ログインエンドポイント
    
    メールアドレスとパスワードでログインし、アクセストークンを取得します
    
    Args:
        user_data: ログイン情報（メールアドレス、パスワード）
    
    Returns:
        dict: ユーザー情報とアクセストークン
    """
    try:
        # ユーザー認証
        user = authenticate_user(user_data.email, user_data.password)
        
        # アクセストークンを生成
        access_token = create_access_token(data={"sub": user["email"]})
        
        return {
            "user": user,
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ログインに失敗しました: {str(e)}"
        )


@app.get("/api/auth/me") # Depends(get_current_user)は、依存関数で毎回get_current_user()が実行されてから始まる。
async def get_current_user_info(current_user: dict = Depends(get_current_user)): 
    """
    現在ログインしているユーザー情報を取得するエンドポイント
    
    Args:
        current_user: 認証されたユーザー情報（依存関数から取得）
    
    Returns:
        dict: ユーザー情報
    """
    return current_user

# ========== 予約関連のAPIエンドポイント ==========

@app.post("/api/reservations")
async def create_reservation(
    reservation_data: ReservationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    予約を作成するエンドポイント
    
    ログインしているユーザーが予約を作成します
    
    Args:
        reservation_data: 予約情報（日付、時間、人数、特別な要望）
        current_user: 認証されたユーザー情報
    
    Returns:
        dict: 作成された予約情報
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # 予約時間を文字列からtimeオブジェクトに変換
        reservation_time_obj = time.fromisoformat(reservation_data.reservation_time)
        
        # 予約をデータベースに挿入
        cursor.execute(
            """
            INSERT INTO reservations (user_id, reservation_date, reservation_time, number_of_people, special_requests)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, user_id, reservation_date, reservation_time, number_of_people, special_requests, status, created_at
            """,
            (
                current_user["id"],
                reservation_data.reservation_date,
                reservation_time_obj,
                reservation_data.number_of_people,
                reservation_data.special_requests
            )
        )
        
        reservation = cursor.fetchone()
        conn.commit()
        
        # 時間を文字列に変換して返す
        reservation_dict = dict(reservation)
        if reservation_dict["reservation_time"]:
            reservation_dict["reservation_time"] = str(reservation_dict["reservation_time"])
        
        # Slackに予約確定通知を送信（非同期で実行、エラーが発生しても予約処理は続行）
        try:
            notify_reservation_confirmed(
                reservation_id=reservation_dict["id"],
                user_name=current_user["name"],
                user_email=current_user["email"],
                reservation_date=str(reservation_dict["reservation_date"]),
                reservation_time=str(reservation_dict["reservation_time"]),
                number_of_people=reservation_dict["number_of_people"],
                special_requests=reservation_dict.get("special_requests")
            )
        except Exception as e:
            # Slack通知のエラーはログに記録するが、予約処理自体は成功とする
            print(f"Slack通知送信エラー: {str(e)}")
        
        return reservation_dict
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予約の作成に失敗しました: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@app.get("/api/reservations")
async def get_reservations(current_user: dict = Depends(get_current_user)):
    """
    現在ログインしているユーザーの予約一覧を取得するエンドポイント
    
    Args:
        current_user: 認証されたユーザー情報
    
    Returns:
        list: 予約一覧
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # ユーザーの予約を取得
        cursor.execute(
            """
            SELECT id, user_id, reservation_date, reservation_time, number_of_people, special_requests, status, created_at
            FROM reservations
            WHERE user_id = %s
            ORDER BY reservation_date DESC, reservation_time DESC
            """,
            (current_user["id"],)
        )
        
        reservations = cursor.fetchall()
        
        # 時間を文字列に変換
        result = []
        for reservation in reservations:
            reservation_dict = dict(reservation)
            if reservation_dict["reservation_time"]:
                reservation_dict["reservation_time"] = str(reservation_dict["reservation_time"])
            result.append(reservation_dict)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予約の取得に失敗しました: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@app.delete("/api/reservations/{reservation_id}")
async def cancel_reservation(
    reservation_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    予約をキャンセルするエンドポイント
    
    Args:
        reservation_id: 予約ID
        current_user: 認証されたユーザー情報
    
    Returns:
        dict: キャンセルされた予約情報
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # 予約が存在し、ユーザーが所有しているか確認
        cursor.execute(
            "SELECT * FROM reservations WHERE id = %s AND user_id = %s",
            (reservation_id, current_user["id"])
        )
        reservation = cursor.fetchone()
        
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="予約が見つかりません"
            )
        
        # 予約情報を取得（通知用）
        reservation_dict = dict(reservation)
        reservation_date = str(reservation_dict["reservation_date"])
        reservation_time = str(reservation_dict["reservation_time"]) if reservation_dict["reservation_time"] else ""
        number_of_people = reservation_dict["number_of_people"]
        
        # 予約を削除
        cursor.execute(
            "DELETE FROM reservations WHERE id = %s AND user_id = %s",
            (reservation_id, current_user["id"])
        )
        conn.commit()
        
        # Slackに予約キャンセル通知を送信（非同期で実行、エラーが発生してもキャンセル処理は続行）
        try:
            notify_reservation_cancelled(
                reservation_id=reservation_id,
                user_name=current_user["name"],
                user_email=current_user["email"],
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                number_of_people=number_of_people
            )
        except Exception as e:
            # Slack通知のエラーはログに記録するが、キャンセル処理自体は成功とする
            print(f"Slack通知送信エラー: {str(e)}")
        
        return {"message": "予約がキャンセルされました", "reservation_id": reservation_id}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予約のキャンセルに失敗しました: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()
