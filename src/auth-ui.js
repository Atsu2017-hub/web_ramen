// 認証UI（ログイン・登録フォーム）を管理するJavaScriptモジュール

import { login, register, getCurrentUser, logout } from "./auth.js";
import { loadReservations } from "./reservation-ui.js";

// ログインフォームの表示・非表示を切り替える関数
function showLoginForm() {
    document.getElementById("login-form").style.display = "block";
    document.getElementById("register-form").style.display = "none";
}

// 登録フォームの表示・非表示を切り替える関数
function showRegisterForm() {
    document.getElementById("login-form").style.display = "none";
    document.getElementById("register-form").style.display = "block";
}

// 認証フォームを非表示にする関数
function hideAuthForms() {
    document.getElementById("login-form").style.display = "none";
    document.getElementById("register-form").style.display = "none";
}

// ユーザー情報を表示する関数
function showUserInfo(user) {
    const userInfoDiv = document.getElementById("user-info");
    if (userInfoDiv) {
        userInfoDiv.innerHTML = `
            <div class="user-info-content">
                <p>ようこそ、<strong>${user.name}</strong>さん</p>
                <p class="user-email">${user.email}</p>
                <button id="logout-btn" class="btn btn-secondary">ログアウト</button>
            </div>
        `;
        
        // ログアウトボタンのイベントリスナーを追加
        document.getElementById("logout-btn").addEventListener("click", () => {
            logout();
        });
    }
}

// 認証状態を更新する関数（ログイン状態に応じてUIを切り替え）
async function updateAuthUI() {
    const user = await getCurrentUser();
    const reservationSection = document.getElementById("reservation-section");
    
    if (user) {
        // ログインしている場合
        hideAuthForms();
        showUserInfo(user);
        // 予約セクションを表示
        if (reservationSection) {
            reservationSection.style.display = "block";
            // 予約一覧を読み込む
            try {
                await loadReservations();
            } catch (error) {
                console.error("予約一覧の読み込みに失敗しました:", error);
            }
        }
    } else {
        // ログインしていない場合
        const userInfoDiv = document.getElementById("user-info");
        if (userInfoDiv) {
            userInfoDiv.innerHTML = "";
        }
        showLoginForm();
        // 予約セクションを非表示
        if (reservationSection) {
            reservationSection.style.display = "none";
        }
    }
}

// ログインフォームの送信処理
async function handleLogin(event) {
    event.preventDefault(); // フォームのデフォルトの送信を防止。これをしないとページがリロードされてしまう。
    
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    const errorDiv = document.getElementById("login-error");
    
    try {
        errorDiv.textContent = "";
        errorDiv.style.display = "none";
        
        await login(email, password);
        await updateAuthUI(); //ログイン成功後にUIを更新。
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = "block";
    }
}

// 登録フォームの送信処理
async function handleRegister(event) {
    event.preventDefault();
    
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;
    const name = document.getElementById("register-name").value;
    const errorDiv = document.getElementById("register-error");
    
    try {
        errorDiv.textContent = "";
        errorDiv.style.display = "none";
        
        await register(email, password, name);
        await updateAuthUI();
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = "block";
    }
}

// 初期化関数
function initAuthUI() {
    // フォームのイベントリスナーを設定
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
    
    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener("submit", handleRegister);
    }
    
    // フォーム切り替えボタンのイベントリスナー
    const showRegisterLink = document.getElementById("show-register");
    const showLoginLink = document.getElementById("show-login");
    
    if (showRegisterLink) {
        showRegisterLink.addEventListener("click", (e) => {
            e.preventDefault();
            showRegisterForm();
        });
    }
    
    if (showLoginLink) {
        showLoginLink.addEventListener("click", (e) => {
            e.preventDefault();
            showLoginForm();
        });
    }
    
    // ページ読み込み時に認証状態を確認
    updateAuthUI();
}

// DOMContentLoadedイベントで初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuthUI);
} else {
    initAuthUI();
}

// 他のモジュールから使用できるようにエクスポート
export { updateAuthUI };

