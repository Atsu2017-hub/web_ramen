// 予約機能を管理するJavaScriptモジュール
// 予約の作成、取得、キャンセルを行う

import { authenticatedFetch, API_BASE_URL } from "./auth.js";

// 予約を作成する関数
// reservationDataには以下のフィールドを含めることができます:
// - reservation_date: 予約日
// - reservation_time: 予約時間
// - number_of_people: 人数
// - special_requests: 特別な要望（任意）
// - menu_items: メニューアイテムの配列 [{ menu_id: number, quantity: number }]
// - payment_intent_id: StripeのPayment Intent ID
async function createReservation(reservationData) {
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/reservations`, {
            method: "POST",
            body: JSON.stringify(reservationData),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "予約の作成に失敗しました");
        }

        return await response.json();
    } catch (error) {
        console.error("予約作成エラー:", error);
        throw error;
    }
}

// 予約一覧を取得する関数
async function getReservations() {
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/reservations`, {
            method: "GET",
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "予約の取得に失敗しました");
        }

        return await response.json();
    } catch (error) {
        console.error("予約取得エラー:", error);
        throw error;
    }
}

// 予約をキャンセルする関数
async function cancelReservation(reservationId) {
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/reservations/${reservationId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "予約のキャンセルに失敗しました");
        }

        return await response.json();
    } catch (error) {
        console.error("予約キャンセルエラー:", error);
        throw error;
    }
}

// モジュールとしてエクスポート
export { createReservation, getReservations, cancelReservation };

