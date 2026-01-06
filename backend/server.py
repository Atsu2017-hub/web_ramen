# FastAPIを使用。これでHTTPサーバを構築。
# OpenAIを使用。これでOpenAIのAPIを呼び出す。
# osを使用。これで環境変数を取得。
# dotenvを使用。これで.envファイルから環境変数を読み込む。

from fastapi import FastAPI, Request, Depends, HTTPException, status  # pyright: ignore[reportMissingImports]
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # pyright: ignore[reportMissingImports]
from openai import OpenAI  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, EmailStr  # pyright: ignore[reportMissingImports]
from typing import Any, Dict, Optional, List  # pyright: ignore[reportMissingImports]
from datetime import date, time  # pyright: ignore[reportMissingImports]
import os  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
import stripe  # pyright: ignore[reportMissingImports]

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

# StripeのAPIキーを環境変数から取得して設定
# Stripe API: 決済処理を行うためのAPI。秘密鍵（sk_で始まる）をサーバー側で使用
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

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

# メニューアイテム用のリクエストモデル
class MenuItemRequest(BaseModel):
    menu_id: int  # メニューID
    quantity: int  # 数量

# 予約作成用のリクエストモデル
class ReservationCreate(BaseModel):
    reservation_date: date  # 予約日
    reservation_time: str  # 予約時間（文字列形式、例: "18:00"）
    number_of_people: int  # 人数
    special_requests: Optional[str] = None  # 特別な要望（任意）
    menu_items: Optional[List[MenuItemRequest]] = []  # 選択されたメニューアイテム
    payment_intent_id: Optional[str] = None  # StripeのPayment Intent ID

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

# ========== メニュー関連のAPIエンドポイント ==========

@app.get("/api/stripe/publishable-key")
async def get_stripe_publishable_key():
    """
    Stripe公開可能キーを取得するエンドポイント
    
    Stripe API: クライアント側でStripe.jsを使用する際に必要な公開可能キー（pk_で始まる）
    を返す。秘密鍵（sk_で始まる）とは異なり、クライアント側に公開しても安全。
    
    Returns:
        dict: Stripe公開可能キー
    """
    publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    if not publishable_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe公開可能キーが設定されていません"
        )
    return {"publishable_key": publishable_key}


@app.get("/api/menus")
async def get_menus():
    """
    利用可能なメニュー一覧を取得するエンドポイント
    
    Returns:
        list: メニュー一覧
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        cursor.execute(
            """
            SELECT id, name, description, price, image_url, is_available
            FROM menus
            WHERE is_available = TRUE
            ORDER BY id
            """
        )
        menus = cursor.fetchall()
        return [dict(menu) for menu in menus]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メニューの取得に失敗しました: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


# ========== 決済関連のAPIエンドポイント ==========

@app.post("/api/payments/create-intent")
async def create_payment_intent(
    menu_items: List[MenuItemRequest],
    current_user: dict = Depends(get_current_user)
):
    """
    Stripe Payment Intentを作成するエンドポイント
    
    Payment Intent: Stripeの決済処理を開始するためのオブジェクト。
    クライアント側でStripe.jsを使用して決済を完了させるために必要。
    
    Args:
        menu_items: 選択されたメニューアイテムのリスト
        current_user: 認証されたユーザー情報
    
    Returns:
        dict: Payment Intent情報（client_secretを含む）
    """
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe APIキーが設定されていません"
        )
    
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # メニュー情報を取得して合計金額を計算
        total_amount = 0
        menu_ids = [item.menu_id for item in menu_items]
        
        if not menu_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="メニューが選択されていません"
            )
        
        # メニュー情報を取得
        placeholders = ','.join(['%s'] * len(menu_ids))
        cursor.execute(
            f"""
            SELECT id, name, price, is_available
            FROM menus
            WHERE id IN ({placeholders})
            """,
            menu_ids
        )
        # id: メニュー情報
        menus = {menu['id']: menu for menu in cursor.fetchall()}
        
        # 合計金額を計算
        for item in menu_items:
            if item.menu_id not in menus:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"メニューID {item.menu_id} が見つかりません"
                )
            if not menus[item.menu_id]['is_available']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"メニュー「{menus[item.menu_id]['name']}」は現在利用できません"
                )
            total_amount += menus[item.menu_id]['price'] * item.quantity
        
        if total_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="合計金額が0円以下です"
            )
        
        # Stripe Payment Intentを作成
        # amountは最小通貨単位（日本円の場合は円単位）
        # currency: 通貨コード（'jpy'は日本円）
        # automatic_payment_methods: 利用可能な決済方法を自動で有効化（PaymentElement向け）
        # metadata: 追加情報（ユーザーIDやメニュー情報などを保存可能）
        payment_intent = stripe.PaymentIntent.create(
            amount=total_amount,  # 金額（日本円の場合は円単位）
            currency='jpy',  # 通貨コード
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'user_id': str(current_user['id']),
                'user_email': current_user['email']
            }
        )
        
        # client_secret: クライアント側でStripe.jsを使用して決済を完了させるために必要な秘密鍵
        return {
            'client_secret': payment_intent.client_secret, #必須
            'payment_intent_id': payment_intent.id,
            'amount': total_amount
        }
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripeエラー: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment Intentの作成に失敗しました: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@app.post("/api/payments/refund/{payment_intent_id}")
async def refund_payment(
    payment_intent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    決済を返金するエンドポイント
    
    Refund: Stripeで既に決済完了したPayment Intentを返金する処理。
    返金は全額返金のみ（部分返金も可能だが、ここでは全額返金のみ実装）。
    
    Args:
        payment_intent_id: StripeのPayment Intent ID
        current_user: 認証されたユーザー情報
    
    Returns:
        dict: 返金情報
    """
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe APIキーが設定されていません"
        )
    
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # 予約が存在し、ユーザーが所有しているか確認
        cursor.execute(
            """
            SELECT id, payment_intent_id, payment_status, amount
            FROM reservations
            WHERE payment_intent_id = %s AND user_id = %s
            """,
            (payment_intent_id, current_user["id"])
        )
        reservation = cursor.fetchone()
        
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="予約が見つかりません"
            )
        
        reservation_dict = dict(reservation)
        
        # 既に返金済みか確認
        if reservation_dict['payment_status'] == 'refunded':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="既に返金済みです"
            )
        
        # Payment Intentを取得して返金
        # Stripe API: Payment Intentを取得して、そのCharge IDを取得
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # 決済が完了しているか確認
        if payment_intent.status != 'succeeded':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="決済が完了していないため返金できません"
            )
        
        # Charge IDを取得（返金に必要）
        charge_id = payment_intent.latest_charge
        if not charge_id:
            # latest_chargeが文字列の場合
            if isinstance(payment_intent.latest_charge, str):
                charge_id = payment_intent.latest_charge
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Charge IDが見つかりません"
                )
        
        # Refundを作成（全額返金）
        # Stripe API: Refund.create()で返金処理を実行
        # charge: 返金するCharge ID
        # amount: 返金額（指定しない場合は全額返金）
        refund = stripe.Refund.create(
            charge=charge_id,
            # amountを指定しない場合は全額返金
        )
        
        # 予約の決済ステータスを更新
        cursor.execute(
            """
            UPDATE reservations
            SET payment_status = 'refunded'
            WHERE id = %s
            """,
            (reservation_dict['id'],)
        )
        conn.commit()
        
        return {
            'refund_id': refund.id,
            'amount': refund.amount,
            'status': refund.status,
            'message': '返金が完了しました'
        }
    except stripe.error.StripeError as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripeエラー: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"返金処理に失敗しました: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


# ========== 予約関連のAPIエンドポイント ==========

@app.post("/api/reservations")
async def create_reservation(
    reservation_data: ReservationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    予約を作成するエンドポイント
    
    ログインしているユーザーが予約を作成します。
    決済が完了している必要があります（payment_intent_idが必要）。
    
    Args:
        reservation_data: 予約情報（日付、時間、人数、特別な要望、メニュー、決済情報）
        current_user: 認証されたユーザー情報
    
    Returns:
        dict: 作成された予約情報
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # Payment Intentが指定されている場合、決済が完了しているか確認
        payment_status = 'pending'
        amount = None
        
        if reservation_data.payment_intent_id:
            if not stripe.api_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Stripe APIキーが設定されていません"
                )
            
            # Stripe API: Payment Intentの状態を確認
            # statusが'succeeded'の場合、決済が完了している
            payment_intent = stripe.PaymentIntent.retrieve(reservation_data.payment_intent_id)
            
            if payment_intent.status != 'succeeded':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="決済が完了していません"
                )
            
            payment_status = 'succeeded'
            amount = payment_intent.amount
        
        # 予約時間を文字列からtimeオブジェクトに変換
        reservation_time_obj = time.fromisoformat(reservation_data.reservation_time)
        
        # 予約をデータベースに挿入
        cursor.execute(
            """
            INSERT INTO reservations (user_id, reservation_date, reservation_time, number_of_people, special_requests, payment_intent_id, amount, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, reservation_date, reservation_time, number_of_people, special_requests, status, payment_intent_id, amount, payment_status, created_at
            """,
            (
                current_user["id"],
                reservation_data.reservation_date,
                reservation_time_obj,
                reservation_data.number_of_people,
                reservation_data.special_requests,
                reservation_data.payment_intent_id,
                amount,
                payment_status
            )
        )
        
        reservation = cursor.fetchone()
        reservation_dict = dict(reservation)
        reservation_id = reservation_dict["id"]
        
        # メニューアイテムを挿入
        if reservation_data.menu_items:
            for menu_item in reservation_data.menu_items:
                cursor.execute(
                    """
                    INSERT INTO reservation_menu_items (reservation_id, menu_id, quantity)
                    VALUES (%s, %s, %s)
                    """,
                    (reservation_id, menu_item.menu_id, menu_item.quantity)
                )
        
        conn.commit()
        
        # 時間を文字列に変換して返す
        if reservation_dict["reservation_time"]:
            reservation_dict["reservation_time"] = str(reservation_dict["reservation_time"])
        
        # メニュー情報を取得して追加
        if reservation_data.menu_items:
            menu_ids = [item.menu_id for item in reservation_data.menu_items]
            placeholders = ','.join(['%s'] * len(menu_ids))
            cursor.execute(
                f"""
                SELECT m.id, m.name, m.price, rmi.quantity
                FROM menus m
                INNER JOIN reservation_menu_items rmi ON m.id = rmi.menu_id
                WHERE rmi.reservation_id = %s AND m.id IN ({placeholders})
                """,
                [reservation_id] + menu_ids
            )
            menu_items = cursor.fetchall()
            reservation_dict["menu_items"] = [dict(item) for item in menu_items]
        
        # Slackに予約確定通知を送信（非同期で実行、エラーが発生しても予約処理は続行）
        try:
            notify_reservation_confirmed(
                reservation_id=reservation_dict["id"],
                user_name=current_user["name"],
                user_email=current_user["email"],
                reservation_date=str(reservation_dict["reservation_date"]),
                reservation_time=str(reservation_dict["reservation_time"]),
                number_of_people=reservation_dict["number_of_people"],
                special_requests=reservation_dict.get("special_requests"),
                menu_items=reservation_dict.get("menu_items")
            )
        except Exception as e:
            # Slack通知のエラーはログに記録するが、予約処理自体は成功とする
            print(f"Slack通知送信エラー: {str(e)}")
        
        return reservation_dict
    except HTTPException:
        conn.rollback()
        raise
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
            SELECT id, user_id, reservation_date, reservation_time, number_of_people, special_requests, status, payment_intent_id, amount, payment_status, created_at
            FROM reservations
            WHERE user_id = %s
            ORDER BY reservation_date DESC, reservation_time DESC
            """,
            (current_user["id"],)
        )
        
        reservations = cursor.fetchall()
        
        # 時間を文字列に変換し、メニュー情報を追加
        result = []
        for reservation in reservations:
            reservation_dict = dict(reservation)
            if reservation_dict["reservation_time"]:
                reservation_dict["reservation_time"] = str(reservation_dict["reservation_time"])
            
            # メニュー情報を取得
            cursor.execute(
                """
                SELECT m.id, m.name, m.price, rmi.quantity
                FROM menus m
                INNER JOIN reservation_menu_items rmi ON m.id = rmi.menu_id
                WHERE rmi.reservation_id = %s
                """,
                (reservation_dict["id"],)
            )
            menu_items = cursor.fetchall()
            reservation_dict["menu_items"] = [dict(item) for item in menu_items]
            
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
    
    決済が完了している場合は自動的に返金処理も実行されます。
    
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
            """
            SELECT id, payment_intent_id, payment_status, reservation_date, reservation_time, number_of_people
            FROM reservations
            WHERE id = %s AND user_id = %s
            """,
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
        payment_intent_id = reservation_dict.get("payment_intent_id")
        payment_status = reservation_dict.get("payment_status")
        
        # 決済が完了している場合は返金処理を実行
        refund_info = None
        if payment_intent_id and payment_status == 'succeeded':
            try:
                if stripe.api_key:
                    # Payment Intentを取得
                    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                    
                    if payment_intent.status == 'succeeded':
                        # Charge IDを取得
                        charge_id = payment_intent.latest_charge
                        if isinstance(charge_id, str):
                            # 返金処理を実行
                            refund = stripe.Refund.create(charge=charge_id)
                            refund_info = {
                                'refund_id': refund.id,
                                'amount': refund.amount,
                                'status': refund.status
                            }
                            
                            # 決済ステータスを更新
                            cursor.execute(
                                """
                                UPDATE reservations
                                SET payment_status = 'refunded'
                                WHERE id = %s
                                """,
                                (reservation_id,)
                            )
            except Exception as e:
                # 返金処理のエラーはログに記録するが、キャンセル処理は続行
                print(f"返金処理エラー: {str(e)}")
        
        # 予約を削除（CASCADEにより関連するメニューアイテムも自動削除）
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
        
        response = {"message": "予約がキャンセルされました", "reservation_id": reservation_id}
        if refund_info:
            response["refund"] = refund_info
        
        return response
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
