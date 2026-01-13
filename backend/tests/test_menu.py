"""
メニュー機能のテスト
"""
import pytest
from fastapi import status


class TestGetMenus:
    """メニュー取得のテスト"""
    
    def test_get_menus_success(self, client, test_db, test_menu):
        """正常なメニュー取得"""
        response = client.get("/api/menus")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # テストメニューが含まれているか確認
        menu_ids = [menu["id"] for menu in data]
        assert test_menu["id"] in menu_ids
    
    def test_get_menus_only_available(self, client, test_db):
        """利用可能なメニューのみ取得"""
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
        
        response = client.get("/api/menus")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        menu_ids = [menu["id"] for menu in data]
        assert unavailable_menu_id not in menu_ids

