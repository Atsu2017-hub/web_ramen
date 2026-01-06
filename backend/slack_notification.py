# Slack通知機能を実装するモジュール
# Slack Webhookを使用して予約の決定・キャンセルを通知

import requests  # pyright: ignore[reportMissingImports]
from typing import Dict, Optional  # pyright: ignore[reportMissingImports]
import os  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

# .envファイルから環境変数を読み込む
load_dotenv()

# Slack Webhook URL（環境変数から取得）
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_notification(message: str, blocks: Optional[list] = None) -> bool:
    """
    Slackに通知を送信する関数
    
    Args:
        message: 通知メッセージ（フォールバック用）
        blocks: Slack Block Kit形式のメッセージブロック（オプション）
    
    Returns:
        bool: 送信成功時True、失敗時False
    """
    try:
        payload = {
            "text": message,  # フォールバック用のテキスト
        }
        
        # blocksが指定されている場合は追加
        if blocks:
            payload["blocks"] = blocks
        
        # Slack WebhookにPOSTリクエストを送信
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        
        # ステータスコードが200の場合は成功
        if response.status_code == 200:
            return True
        else:
            print(f"Slack通知エラー: ステータスコード {response.status_code}, レスポンス: {response.text}")
            return False
    except Exception as e:
        print(f"Slack通知送信エラー: {str(e)}")
        return False


def format_reservation_date(date_str: str) -> str:
    """
    予約日を日本語形式にフォーマットする関数
    
    Args:
        date_str: 日付文字列（YYYY-MM-DD形式）
    
    Returns:
        str: フォーマットされた日付文字列（例: 2024年1月15日）
    """
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y年%m月%d日")
    except:
        return date_str


def format_reservation_time(time_str: str) -> str:
    """
    予約時間を日本語形式にフォーマットする関数
    
    Args:
        time_str: 時間文字列（HH:MM:SS形式またはHH:MM形式）
    
    Returns:
        str: フォーマットされた時間文字列（例: 18時00分）
    """
    try:
        # 秒の部分がある場合は除去
        if len(time_str) > 5:
            time_str = time_str[:5]
        
        hour, minute = time_str.split(":")
        return f"{int(hour)}時{int(minute)}分"
    except:
        return time_str


def notify_reservation_confirmed(
    reservation_id: int,
    user_name: str,
    user_email: str,
    reservation_date: str,
    reservation_time: str,
    number_of_people: int,
    special_requests: Optional[str] = None,
    menu_items: Optional[list] = None,
) -> bool:
    """
    予約決定（作成）をSlackに通知する関数
    
    Args:
        reservation_id: 予約ID
        user_name: ユーザー名
        user_email: ユーザーのメールアドレス
        reservation_date: 予約日（YYYY-MM-DD形式）
        reservation_time: 予約時間（HH:MM:SS形式）
        number_of_people: 人数
        special_requests: 特別な要望（オプション）
        menu_items: 予約したメニュー一覧（例: [{\"name\": str, \"quantity\": int, \"price\": int}]）
    
    Returns:
        bool: 送信成功時True、失敗時False
    """
    # 日付と時間をフォーマット
    formatted_date = format_reservation_date(reservation_date)
    formatted_time = format_reservation_time(reservation_time)
    
    # Slack Block Kit形式のメッセージを作成。各ブロックは type とその他のフィールドを記載する.
    # インタラクティブ性を対応させる予定。
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "✅ 新しい予約が確定しました",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*予約ID:*\n#{reservation_id}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*予約日時:*\n{formatted_date} {formatted_time}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*お客様名:*\n{user_name}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*人数:*\n{number_of_people}名"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*メールアドレス:*\n{user_email}"
                }
            ]
        }
    ]
    
    # メニュー情報がある場合は追加
    if menu_items:
        lines = []
        for item in menu_items:
            name = item.get("name", "不明なメニュー")
            quantity = item.get("quantity", 1)
            price = item.get("price")
            if price is not None:
                subtotal = price * quantity
                lines.append(f"- {name} × {quantity}個 (¥{subtotal:,})")
            else:
                lines.append(f"- {name} × {quantity}個")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*注文メニュー:*\n" + "\n".join(lines)
            }
        })
    
    # 特別な要望がある場合は追加
    if special_requests:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*特別な要望:*\n{special_requests}"
            }
        })
    
    # 通知を送信
    message = f"新しい予約が確定しました - 予約ID: #{reservation_id}, お客様: {user_name}, 日時: {formatted_date} {formatted_time}, 人数: {number_of_people}名"
    return send_slack_notification(message, blocks)


def notify_reservation_cancelled(
    reservation_id: int,
    user_name: str,
    user_email: str,
    reservation_date: str,
    reservation_time: str,
    number_of_people: int
) -> bool:
    """
    予約キャンセルをSlackに通知する関数
    
    Args:
        reservation_id: 予約ID
        user_name: ユーザー名
        user_email: ユーザーのメールアドレス
        reservation_date: 予約日（YYYY-MM-DD形式）
        reservation_time: 予約時間（HH:MM:SS形式）
        number_of_people: 人数
    
    Returns:
        bool: 送信成功時True、失敗時False
    """
    # 日付と時間をフォーマット
    formatted_date = format_reservation_date(reservation_date)
    formatted_time = format_reservation_time(reservation_time)
    
    # Slack Block Kit形式のメッセージを作成
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "❌ 予約がキャンセルされました",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*予約ID:*\n#{reservation_id}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*予約日時:*\n{formatted_date} {formatted_time}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*お客様名:*\n{user_name}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*人数:*\n{number_of_people}名"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*メールアドレス:*\n{user_email}"
                }
            ]
        }
    ]
    
    # 通知を送信
    message = f"予約がキャンセルされました - 予約ID: #{reservation_id}, お客様: {user_name}, 日時: {formatted_date} {formatted_time}, 人数: {number_of_people}名"
    return send_slack_notification(message, blocks)

