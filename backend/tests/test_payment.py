"""
決済機能のテスト
"""
import pytest
from fastapi import status


class TestCreatePaymentIntent:
    """Payment Intent作成のテスト"""
    
    def test_create_payment_intent_success(self, client, test_user, test_menu, mock_stripe):
        """正常なPayment Intent作成"""
        menu_items = [
            {"menu_id": test_menu["id"], "quantity": 2}
        ]
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/api/payments/create-intent", json=menu_items, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "client_secret" in data
        assert "payment_intent_id" in data
        assert "amount" in data
        assert data["amount"] == test_menu["price"] * 2
    
    def test_create_payment_intent_no_menu(self, client, test_user):
        """メニューが選択されていない場合"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/api/payments/create-intent", json=[], headers=headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "メニューが選択されていません" in data["detail"]
    
    def test_create_payment_intent_invalid_menu_id(self, client, test_user):
        """存在しないメニューID"""
        menu_items = [
            {"menu_id": 99999, "quantity": 1}
        ]
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/api/payments/create-intent", json=menu_items, headers=headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_payment_intent_unavailable_menu(self, client, test_user, test_db):
        """利用不可メニューの選択"""
        from database import get_db_connection, get_db_cursor
        
        # 利用不可メニューを作成
        conn = get_db_connection()
        cursor = get_db_cursor(conn)
        try:
            cursor.execute("""
                INSERT INTO menus (name, description, price, is_available)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, ("利用不可メニュー", "テスト", 1000, False))
            unavailable_menu_id = cursor.fetchone()["id"]
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        
        menu_items = [
            {"menu_id": unavailable_menu_id, "quantity": 1}
        ]
        
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/api/payments/create-intent", json=menu_items, headers=headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "利用できません" in data["detail"]
    
    def test_create_payment_intent_no_auth(self, client, test_menu):
        """認証なしでのPayment Intent作成"""
        menu_items = [
            {"menu_id": test_menu["id"], "quantity": 1}
        ]
        
        response = client.post("/api/payments/create-intent", json=menu_items)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestRefundPayment:
    """返金機能のテスト"""
    
    def test_refund_payment_success(self, client, test_user, test_menu, mock_stripe):
        """正常な返金処理"""
        from datetime import date, timedelta
        
        # 予約を作成（決済済み）
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
        
        # 返金を実行
        payment_intent_id = "pi_test_123"
        response = client.post(
            f"/api/payments/refund/{payment_intent_id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "refund_id" in data
        assert "amount" in data
        assert "status" in data
        assert data["status"] == "succeeded"
    
    def test_refund_payment_not_found(self, client, test_user):
        """存在しない予約の返金"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post(
            "/api/payments/refund/pi_nonexistent",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_refund_payment_already_refunded(self, client, test_user, test_menu, mock_stripe):
        """既に返金済みの場合"""
        from datetime import date, timedelta
        
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
        client.post("/api/reservations", json=reservation_data, headers=headers)
        
        # 1回目の返金
        payment_intent_id = "pi_test_123"
        client.post(f"/api/payments/refund/{payment_intent_id}", headers=headers)
        
        # 2回目の返金（エラーになるはず）
        response = client.post(
            f"/api/payments/refund/{payment_intent_id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "返金済み" in data["detail"]
    
    def test_refund_payment_no_auth(self, client):
        """認証なしでの返金"""
        response = client.post("/api/payments/refund/pi_test_123")
        assert response.status_code == status.HTTP_403_FORBIDDEN

