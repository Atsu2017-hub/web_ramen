# 認証機能を実装するモジュール
# JWT（JSON Web Token）を使用してセッション管理を行う

from datetime import datetime, timedelta, timezone
from typing import Any  # 日時処理用
from jose import JWTError, jwt  # JWTトークンの生成・検証用
from passlib.context import CryptContext  # パスワードのハッシュ化用
from fastapi import HTTPException, status  # HTTP例外処理用
from database import get_db_connection, get_db_cursor  # データベース接続用
import os  # 環境変数の取得に使用
from dotenv import load_dotenv  # .envファイルから環境変数を読み込む

# .envファイルから環境変数を読み込む
load_dotenv()

# パスワードハッシュ化の設定
# bcryptアルゴリズムを使用してパスワードをハッシュ化
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT設定
# 環境変数から取得（開発環境用のデフォルト値を設定）
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")  # JWT署名用の秘密鍵
ALGORITHM = "HS256"  # JWT署名アルゴリズム
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # トークンの有効期限（30分）


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    平文パスワードとハッシュ化されたパスワードを照合する関数
    
    Args:
        plain_password: 平文のパスワード
        hashed_password: ハッシュ化されたパスワード
    
    Returns:
        bool: パスワードが一致する場合True
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    パスワードをハッシュ化する関数
    
    Args:
        password: 平文のパスワード
    
    Returns:
        str: ハッシュ化されたパスワード
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    JWT(JSON Web Token)アクセストークンを生成する関数
    アクセストークンは、ログイン後にサーバーから発行される文字列で、
    ユーザーが「ログイン済み」であることを示します。
    以降のリクエストで、パスワードを送らずにこのトークンを使って認証できます。
    
    Args:
        data: トークンに含めるデータ（例: ユーザーID、メールアドレス）
        expires_delta: 有効期限（指定しない場合はデフォルト値を使用）
    
    Returns:
        str: JWTトークン
    """
    # トークンに含めるデータをコピー
    to_encode = data.copy()
    
    # 有効期限の設定
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 有効期限をトークンデータに追加
    to_encode.update({"exp": expire}) # updateメソッドは、辞書に新しいキーと値を追加する(キー被りは上書き)。
    
    # JWTトークンを生成。SECRET_KEYはJWT署名用の秘密鍵で環境変数に追加。
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    JWTトークンを検証し、含まれるデータを返す関数
    
    Args:
        token: JWTトークン
    
    Returns:
        dict: トークンに含まれるデータ（ユーザー情報など）
    
    Raises:
        HTTPException: トークンが無効な場合
    """
    try:
        # トークンをデコード（署名検証も同時に実行）
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # トークンが無効な場合、401エラーを返す
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_by_email(email: str) -> dict:
    """
    メールアドレスでユーザーを検索する関数
    
    Args:
        email: メールアドレス
    
    Returns:
        dict: ユーザー情報（見つからない場合はNone）
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # メールアドレスでユーザーを検索。プレースホルダでSQLインジェクションに対応。
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,)) # タプル形式(1つの要素で,あり)でパラメータを渡す
        user = cursor.fetchone()
        return dict[Any, Any](user) if user else None
    finally:
        cursor.close()
        conn.close()


def create_user(email: str, password: str, name: str) -> dict:
    """
    新しいユーザーを作成する関数
    
    Args:
        email: メールアドレス
        password: 平文のパスワード
        name: ユーザー名
    
    Returns:
        dict: 作成されたユーザー情報
    
    Raises:
        HTTPException: メールアドレスが既に登録されている場合
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    try:
        # パスワードをハッシュ化
        password_hash = get_password_hash(password)
        
        # ユーザーをデータベースに挿入
        cursor.execute(
            """
            INSERT INTO users (email, password_hash, name)
            VALUES (%s, %s, %s)
            RETURNING id, email, name, created_at
            """,
            (email, password_hash, name)
        )
        
        user = cursor.fetchone()
        conn.commit()
        return dict[Any, Any](user) if user else None
    except Exception as e:
        conn.rollback()
        # 既にメールアドレスが登録されている場合
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このメールアドレスは既に登録されています"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー作成に失敗しました"
        )
    finally:
        cursor.close()
        conn.close()


def authenticate_user(email: str, password: str) -> dict:
    """
    ユーザー認証を行う関数
    
    Args:
        email: メールアドレス
        password: 平文のパスワード
    
    Returns:
        dict: 認証されたユーザー情報
    
    Raises:
        HTTPException: 認証に失敗した場合
    """
    # ユーザーをデータベースから検索。
    user = get_user_by_email(email)
    
    if not user:
        # ユーザーが見つからない場合
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="んメールアドレスまたはパスワードが正しくありませ"
        )
    
    # パスワードを照合
    if not verify_password(password, user["password_hash"]):
        # パスワードが一致しない場合
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません"
        )
    
    # パスワードハッシュを返さないようにする（セキュリティのため）
    user.pop("password_hash", None)
    return user

