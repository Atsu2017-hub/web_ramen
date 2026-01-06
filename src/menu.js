// メニュー機能を管理するJavaScriptモジュール
// メニューの取得を行う

import { authenticatedFetch, API_BASE_URL } from "./auth.js";

// メニュー一覧を取得する関数
async function getMenus() {
    try {
        // メニュー取得は認証不要なので、通常のfetchを使用
        const response = await fetch(`${API_BASE_URL}/api/menus`, {
            method: "GET",
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "メニューの取得に失敗しました");
        }

        return await response.json();
    } catch (error) {
        console.error("メニュー取得エラー:", error);
        throw error;
    }
}

// モジュールとしてエクスポート
export { getMenus };

