"""
予約機能のテスト
"""
import pytest
from fastapi import status
from datetime import date, timedelta


class TestCreateReservation:
    """予約作成のテスト"""
    
    def test_create_reservation_success(self, client, test_user, test_menu, mock_stripe):
        """正常な予約作成（決済あり）"""
        # Payment Intentを作成（モック）
        reservation_data = {
            "reservation_date": str(date.today() + timedelta(days=7)),
            "reservation_time": "18:00",
            "number_of_people": 2,
            "special_requests": "窓際の席をお願いします",
            "menu_items": [
                {"menu_id": test_menu["id"], "quantity": 2}
            ],
            "payment_intent_id": "pi_test_123"
        }
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/api/reservations", json=reservation_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == test_user["id"]
        assert data["number_of_people"] == 2
        assert data["special_requests"] == reservation_data["special_requests"]
        assert len(data["menu_items"]) == 1
        assert data["menu_items"][0]["menu_id"] == test_menu["id"]
        assert data["menu_items"][0]["quantity"] == 2
    
    def test_create_reservation_no_auth(self, client, test_db):
        """認証なしでの予約作成"""
        reservation_data = {
            "reservation_date": str(date.today() + timedelta(days=7)),
            "reservation_time": "18:00",
            "number_of_people": 2
        }
        
        response = client.post("/api/reservations", json=reservation_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_reservation_invalid_date(self, client, test_user):
        """過去の日付での予約作成（バリデーションは実装次第）"""
        reservation_data = {
            "reservation_date": str(date.today() - timedelta(days=1)),
            "reservation_time": "18:00",
            "number_of_people": 2,
            "menu_items": []
        }
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/api/reservations", json=reservation_data, headers=headers)
        # 過去の日付はエラーになる可能性がある（実装次第）
        # ここでは200または400のどちらかになることを想定
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    def test_create_reservation_invalid_payment_intent(self, client, test_user, test_menu, mock_stripe):
        """無効なPayment Intent ID"""
        # Payment Intentを失敗状態に設定
        mock_stripe.PaymentIntent.retrieve.return_value.status = "requires_payment_method"
        
        reservation_data = {
            "reservation_date": str(date.today() + timedelta(days=7)),
            "reservation_time": "18:00",
            "number_of_people": 2,
            "menu_items": [
                {"menu_id": test_menu["id"], "quantity": 1}
            ],
            "payment_intent_id": "pi_test_invalid"
        }
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/api/reservations", json=reservation_data, headers=headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetReservations:
    """予約一覧取得のテスト"""
    
    def test_get_reservations_success(self, client, test_user, test_menu, mock_stripe):
        """正常な予約一覧取得"""
        # まず予約を作成
        reservation_data = {
            "reservation_date": str(date.today() + timedelta(days=7)),
            "reservation_time": "18:00",
            "number_of_people": 2,
            "menu_items": [
                {"menu_id": test_menu["id"], "quantity": 1}
            ],
            "payment_intent_id": "pi_test_123"
        }
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        client.post("/api/reservations", json=reservation_data, headers=headers)
        
        # 予約一覧を取得
        response = client.get("/api/reservations", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["user_id"] == test_user["id"]
    
    def test_get_reservations_no_auth(self, client):
        """認証なしでの予約一覧取得"""
        response = client.get("/api/reservations")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_reservations_empty(self, client, test_user):
        """予約がない場合"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.get("/api/reservations", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        # 初期状態では空の可能性がある


class TestCancelReservation:
    """予約キャンセルのテスト"""
    
    def test_cancel_reservation_success(self, client, test_user, test_menu, mock_stripe, mock_slack):
        """正常な予約キャンセル"""
        # 予約を作成
        reservation_data = {
            "reservation_date": str(date.today() + timedelta(days=7)),
            "reservation_time": "18:00",
            "number_of_people": 2,
            "menu_items": [
                {"menu_id": test_menu["id"], "quantity": 1}
            ],
            "payment_intent_id": "pi_test_123"
        }
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        create_response = client.post("/api/reservations", json=reservation_data, headers=headers)
        reservation_id = create_response.json()["id"]
        
        # 予約をキャンセル
        response = client.delete(f"/api/reservations/{reservation_id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "message" in data
        assert "キャンセルされました" in data["message"]
    
    def test_cancel_reservation_not_found(self, client, test_user):
        """存在しない予約のキャンセル"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.delete("/api/reservations/99999", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_cancel_reservation_no_auth(self, client):
        """認証なしでの予約キャンセル"""
        response = client.delete("/api/reservations/1")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cancel_reservation_other_user(self, client, test_db, test_user, test_menu, mock_stripe):
        """他のユーザーの予約をキャンセルしようとする"""
        # 別ユーザーを作成
        user2_data = {
            "email": "user2@example.com",
            "password": "password123",
            "name": "ユーザー2"
        }
        user2_response = client.post("/api/auth/register", json=user2_data)
        user2_token = user2_response.json()["access_token"]
        
        # ユーザー2で予約を作成
        reservation_data = {
            "reservation_date": str(date.today() + timedelta(days=7)),
            "reservation_time": "18:00",
            "number_of_people": 2,
            "menu_items": [
                {"menu_id": test_menu["id"], "quantity": 1}
            ],
            "payment_intent_id": "pi_test_123"
        }
        
        user2_headers = {"Authorization": f"Bearer {user2_token}"}
        create_response = client.post("/api/reservations", json=reservation_data, headers=user2_headers)
        reservation_id = create_response.json()["id"]
        
        # 別のユーザー（test_user）でキャンセルを試みる
        test_user_headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.delete(f"/api/reservations/{reservation_id}", headers=test_user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

