"""
認証モジュール（auth.py）のユニットテスト
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    get_user_by_email,
    create_user,
    authenticate_user
)


class TestPasswordFunctions:
    """パスワード関連関数のテスト"""
    
    def test_get_password_hash(self):
        """パスワードハッシュ化のテスト"""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # 同じパスワードでもハッシュは異なる（saltがランダム）
        assert hash1 != hash2
        assert len(hash1) > 0
        assert len(hash2) > 0
    
    def test_verify_password(self):
        """パスワード検証のテスト"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False


class TestTokenFunctions:
    """トークン関連関数のテスト"""
    
    def test_create_access_token(self):
        """アクセストークン作成のテスト"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_success(self):
        """トークン検証（成功）のテスト"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload["sub"] == "test@example.com"
    
    def test_verify_token_invalid(self):
        """無効なトークンの検証"""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid_token_string")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserFunctions:
    """ユーザー関連関数のテスト"""
    
    @patch('auth.get_db_connection')
    @patch('auth.get_db_cursor') # ここが一番目のモック
    def test_get_user_by_email_found(self, mock_get_cursor, mock_get_conn): # @patchで指定した関数のモック
        """メールアドレスでユーザーを検索（見つかる場合）"""
        # モックの設定
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "email": "test@example.com",
            "name": "テストユーザー",
            "password_hash": "hashed_password"
        }
        mock_get_cursor.return_value = mock_cursor
        
        user = get_user_by_email("test@example.com")
        assert user is not None
        assert user["email"] == "test@example.com"
        mock_cursor.execute.assert_called_once()
    
    @patch('auth.get_db_connection')
    @patch('auth.get_db_cursor')
    def test_get_user_by_email_not_found(self, mock_get_cursor, mock_get_conn):
        """メールアドレスでユーザーを検索（見つからない場合）"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_get_cursor.return_value = mock_cursor
        
        user = get_user_by_email("nonexistent@example.com")
        assert user is None
    
    @patch('auth.get_db_connection')
    @patch('auth.get_db_cursor')
    def test_create_user_success(self, mock_get_cursor, mock_get_conn):
        """ユーザー作成（成功）のテスト"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "email": "new@example.com",
            "name": "新規ユーザー",
            "created_at": "2024-01-01T00:00:00"
        }
        mock_get_cursor.return_value = mock_cursor
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        user = create_user("new@example.com", "password123", "新規ユーザー")
        assert user is not None
        assert user["email"] == "new@example.com"
        mock_conn.commit.assert_called_once()
    
    @patch('auth.get_db_connection')
    @patch('auth.get_db_cursor')
    def test_create_user_duplicate_email(self, mock_get_cursor, mock_get_conn):
        """重複メールアドレスでのユーザー作成"""
        import psycopg2
        
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("unique constraint")
        mock_get_cursor.return_value = mock_cursor
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        with pytest.raises(HTTPException) as exc_info:
            create_user("existing@example.com", "password123", "ユーザー")
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "既に登録されています" in exc_info.value.detail
        mock_conn.rollback.assert_called_once()
    
    @patch('auth.get_user_by_email')
    @patch('auth.verify_password')
    def test_authenticate_user_success(self, mock_verify, mock_get_user):
        """ユーザー認証（成功）のテスト"""
        mock_get_user.return_value = {
            "id": 1,
            "email": "test@example.com",
            "name": "テストユーザー",
            "password_hash": "hashed_password"
        }
        mock_verify.return_value = True
        
        user = authenticate_user("test@example.com", "password123")
        assert user is not None
        assert user["email"] == "test@example.com"
        assert "password_hash" not in user
    
    @patch('auth.get_user_by_email')
    def test_authenticate_user_not_found(self, mock_get_user):
        """ユーザー認証（ユーザーが見つからない場合）"""
        mock_get_user.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            authenticate_user("nonexistent@example.com", "password123")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('auth.get_user_by_email')
    @patch('auth.verify_password')
    def test_authenticate_user_wrong_password(self, mock_verify, mock_get_user):
        """ユーザー認証（パスワードが間違っている場合）"""
        mock_get_user.return_value = {
            "id": 1,
            "email": "test@example.com",
            "name": "テストユーザー",
            "password_hash": "hashed_password"
        }
        mock_verify.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            authenticate_user("test@example.com", "wrongpassword")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

