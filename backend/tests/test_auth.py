"""
認証機能のテスト
"""
import pytest
from fastapi import status


class TestAuthRegister:
    """ユーザー登録のテスト"""
    
    def test_register_success(self, client, test_db):
        """正常な登録"""
        user_data = {
            "email": "newuser@example.com",
            "password": "password123",
            "name": "新規ユーザー"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["name"] == user_data["name"]
        assert "password_hash" not in data["user"]
    
    def test_register_duplicate_email(self, client, test_user):
        """重複メールアドレスでの登録"""
        user_data = {
            "email": test_user["email"],
            "password": "password123",
            "name": "別のユーザー"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response.json()
        assert "既に登録されています" in data["detail"]
    
    def test_register_invalid_email(self, client, test_db):
        """無効なメールアドレス"""
        user_data = {
            "email": "invalid-email",
            "password": "password123",
            "name": "テストユーザー"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthLogin:
    """ログインのテスト"""
    
    def test_login_success(self, client, test_user):
        """正常なログイン"""
        login_data = {
            "email": test_user["email"],
            "password": test_user["password"]
        }
        
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == login_data["email"]
    
    def test_login_wrong_password(self, client, test_user):
        """間違ったパスワード"""
        login_data = {
            "email": test_user["email"],
            "password": "wrongpassword"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        data = response.json()
        assert "正しくありません" in data["detail"]
    
    def test_login_nonexistent_user(self, client, test_db):
        """存在しないユーザー"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthMe:
    """現在のユーザー情報取得のテスト"""
    
    def test_get_current_user_success(self, client, test_user):
        """正常なユーザー情報取得"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]
        assert "password_hash" not in data
    
    def test_get_current_user_no_token(self, client):
        """トークンなしでのアクセス"""
        response = client.get("/api/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_current_user_invalid_token(self, client):
        """無効なトークン"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

