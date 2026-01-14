// 認証機能を管理するJavaScriptモジュール
// ログイン、登録、トークン管理を行う

// バックエンドAPIのベースURL
// - Docker + nginx で動かす場合:
//   フロントとバックエンドは同一オリジン (http://localhost:8080) で nginx が /api を backend にプロキシするため、
//   API_BASE_URL は空文字にして相対パスで叩く。
// - ローカル開発で FastAPI を直接起動する場合:
//   http://localhost:8000 を使う。
const API_BASE_URL =
    window.location.hostname === "localhost" && window.location.port === "8080"
        ? ""                    // nginx 経由で同一オリジン + /api を叩く
        : "http://localhost:8000"; // 直接バックエンドを叩く開発用

// ローカルストレージからトークンを取得する関数
function getToken() {
    return localStorage.getItem("access_token");
}

// ローカルストレージ(フロント側のブラウザ)にトークンを保存する関数
function setToken(token) {
    localStorage.setItem("access_token", token);
}

// ローカルストレージからトークンを削除する関数（ログアウト時に使用）
function removeToken() {
    localStorage.removeItem("access_token");
}

// 現在ログインしているユーザー情報を取得する関数
async function getCurrentUser() {
    const token = getToken();
    if (!token) {
        return null;
    }

    try {
        // 認証が必要なエンドポイントにリクエストを送信
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json",
            },
        });

        if (!response.ok) {
            // トークンが無効な場合、ローカルストレージから削除
            removeToken();
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error("ユーザー情報の取得に失敗しました:", error);
        return null;
    }
}

// ユーザー登録を行う関数
async function register(email, password, name) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ email, password, name }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "登録に失敗しました");
        }

        const data = await response.json();
        // トークンをローカルストレージに保存
        setToken(data.access_token);
        return data;
    } catch (error) {
        console.error("登録エラー:", error);
        throw error;
    }
}

// ログインを行う関数
async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, { // responseはjson形式で返ってくる。
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "ログインに失敗しました");
        }

        const data = await response.json();
        // トークンをローカルストレージに保存
        setToken(data.access_token);
        return data;
    } catch (error) {
        console.error("ログインエラー:", error);
        throw error;
    }
}

// ログアウトを行う関数
function logout() {
    removeToken();
    // ページをリロードして状態をリセット
    window.location.reload();
}

// 認証が必要なAPIリクエストを送信する関数
async function authenticatedFetch(url, options = {}) {
    const token = getToken();
    if (!token) {
        throw new Error("ログインが必要です");
    }

    // 認証ヘッダーを追加
    const headers = {
        ...options.headers, // 既存のヘッダーを保持
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
    };

    const response = await fetch(url, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        // トークンが無効な場合、ログアウト
        removeToken();
        throw new Error("セッションが期限切れです。再度ログインしてください。");
    }

    return response;
}

// モジュールとしてエクスポート（ES6モジュール形式）
export { getToken, setToken, removeToken, getCurrentUser, register, login, logout, authenticatedFetch, API_BASE_URL };

