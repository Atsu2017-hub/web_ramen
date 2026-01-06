// 予約UI（予約フォーム・予約一覧）を管理するJavaScriptモジュール

import { createReservation, getReservations, cancelReservation } from "./reservation.js";
import { getCurrentUser, authenticatedFetch, API_BASE_URL } from "./auth.js";
import { getMenus } from "./menu.js";

// Stripeのインスタンス（公開可能キーを使用）
// Stripe API: クライアント側でStripe.jsを使用する際は公開可能キー（pk_で始まる）を使用
let stripe = null;
let elements = null;         // PaymentElement用のElementsインスタンス
let paymentElement = null;   // PaymentElement本体
let currentPaymentIntent = null; // 現在のPayment Intent情報（client_secret, payment_intent_idなど）
let selectedMenuItems = {}; // { menuId: quantity }

// Stripeを初期化する関数
function initStripe(publishableKey) {
    if (!publishableKey) {
        console.warn("Stripe公開可能キーが設定されていません");
        return;
    }
    
    // Stripeインスタンスを作成
    stripe = Stripe(publishableKey);
    // PaymentElement用のElementsは、Payment Intentのclient_secretが必要なため
    // Payment Intent作成後に初期化する（initPaymentElement関数で実施）
}

// PaymentElementを初期化する関数（Payment Intent作成後に呼び出す）
async function initPaymentElement(clientSecret) {
    if (!stripe) {
        throw new Error("Stripeが初期化されていません");
    }
    
    // 既に初期化済みなら何もしない
    if (elements && paymentElement) {
        return;
    }
    
    // Elementsインスタンスを作成（PaymentElement用）
    elements = stripe.elements({
        clientSecret: clientSecret,
    });
    
    // PaymentElementを作成
    paymentElement = elements.create("payment", {
        layout: "tabs",
    });
    
    // DOMにマウント（payment-elementコンテナにマウント）
    const container = document.getElementById("payment-element");
    if (container) {
        // 既存の内容をクリア
        container.innerHTML = "";
        paymentElement.mount("#payment-element");
        
        // 入力エラーを表示
        paymentElement.on("change", ({ error }) => {
            const displayError = document.getElementById("payment-errors");
            if (error) {
                displayError.textContent = error.message;
                displayError.style.display = "block";
            } else {
                displayError.textContent = "";
                displayError.style.display = "none";
            }
        });
    }
}

// メニュー選択UIを読み込む関数
async function loadMenuSelection() {
    const menuSelection = document.getElementById('menu-selection');
    if (!menuSelection) return;
    
    try {
        const menus = await getMenus();
        
        if (menus.length === 0) {
            menuSelection.innerHTML = '<p>メニューがありません</p>';
            return;
        }
        
        // メニュー選択UIを生成
        menuSelection.innerHTML = menus.map(menu => `
            <div class="menu-select-item">
                <div class="menu-select-info">
                    <h4>${menu.name}</h4>
                    <p>${menu.description || ''}</p>
                    <span class="menu-price">¥${menu.price.toLocaleString()}</span>
                </div>
                <div class="menu-select-controls">
                    <button type="button" class="btn-quantity" data-menu-id="${menu.id}" data-action="decrease">-</button>
                    <span class="quantity-display" data-menu-id="${menu.id}">0</span>
                    <button type="button" class="btn-quantity" data-menu-id="${menu.id}" data-action="increase">+</button>
                </div>
            </div>
        `).join('');
        
        // 数量ボタンのイベントリスナーを追加
        menuSelection.querySelectorAll('.btn-quantity').forEach(button => {
            button.addEventListener('click', (e) => {
                const menuId = parseInt(e.currentTarget.dataset.menuId);
                const action = e.currentTarget.dataset.action;
                
                if (action === 'increase') {
                    selectedMenuItems[menuId] = (selectedMenuItems[menuId] || 0) + 1;
                } else if (action === 'decrease') {
                    selectedMenuItems[menuId] = Math.max(0, (selectedMenuItems[menuId] || 0) - 1);
                    if (selectedMenuItems[menuId] === 0) {
                        delete selectedMenuItems[menuId];
                    }
                }
                
                updateMenuSelection();
                updateSelectedMenuSummary(menus);
            });
        });
    } catch (error) {
        menuSelection.innerHTML = `<p class="error">メニューの読み込みに失敗しました: ${error.message}</p>`;
    }
}

// メニュー選択UIを更新する関数
function updateMenuSelection() {
    document.querySelectorAll('.quantity-display').forEach(display => {
        const menuId = parseInt(display.dataset.menuId);
        display.textContent = selectedMenuItems[menuId] || 0;
    });
}

// 選択されたメニューのサマリーを更新する関数
function updateSelectedMenuSummary(menus) {
    const summaryDiv = document.getElementById('selected-menu-summary');
    const listDiv = document.getElementById('selected-menu-list');
    const totalAmountSpan = document.getElementById('total-amount');
    const paymentSection = document.getElementById('payment-section');
    
    const selectedItems = Object.entries(selectedMenuItems)
        .filter(([_, quantity]) => quantity > 0)
        .map(([menuId, quantity]) => {
            const menu = menus.find(m => m.id === parseInt(menuId));
            return { menu, quantity };
        });
    
    if (selectedItems.length === 0) {
        summaryDiv.style.display = 'none';
        paymentSection.style.display = 'none';
        return;
    }
    
    summaryDiv.style.display = 'block';
    paymentSection.style.display = 'block';
    
    let totalAmount = 0;
    listDiv.innerHTML = selectedItems.map(({ menu, quantity }) => {
        const subtotal = menu.price * quantity;
        totalAmount += subtotal;
        return `
            <div class="selected-menu-item">
                <span>${menu.name} × ${quantity}</span>
                <span>¥${subtotal.toLocaleString()}</span>
            </div>
        `;
    }).join('');
    
    totalAmountSpan.textContent = `¥${totalAmount.toLocaleString()}`;
}

// Payment Intentを作成する関数
async function createPaymentIntent() {
    const menuItems = Object.entries(selectedMenuItems)
        .filter(([_, quantity]) => quantity > 0)
        .map(([menuId, quantity]) => ({
            menu_id: parseInt(menuId),
            quantity: quantity
        }));
    
    if (menuItems.length === 0) {
        throw new Error('メニューを選択してください');
    }
    
    try {
        // Stripe API: サーバー側でPayment Intentを作成
        // client_secretを取得して、クライアント側で決済を完了させる
        const response = await authenticatedFetch(`${API_BASE_URL}/api/payments/create-intent`, {
            method: 'POST',
            body: JSON.stringify(menuItems),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Payment Intentの作成に失敗しました');
        }
        
        const data = await response.json();
        // グローバルに保持して、後続のconfirmで再利用する
        currentPaymentIntent = data;
        return data;
    } catch (error) {
        console.error('Payment Intent作成エラー:', error);
        throw error;
    }
}

// 予約フォームの送信処理
async function handleReservationSubmit(event) {
    event.preventDefault();
    
    const date = document.getElementById("reservation-date").value;
    const time = document.getElementById("reservation-time").value;
    const numberOfPeople = parseInt(document.getElementById("reservation-people").value);
    const specialRequests = document.getElementById("reservation-requests").value;
    const errorDiv = document.getElementById("reservation-error");
    const successDiv = document.getElementById("reservation-success");
    const submitBtn = document.getElementById("submit-reservation-btn");
    
    try {
        errorDiv.textContent = "";
        errorDiv.style.display = "none";
        successDiv.textContent = "";
        successDiv.style.display = "none";
        
        // メニューが選択されているか確認
        const menuItems = Object.entries(selectedMenuItems)
            .filter(([_, quantity]) => quantity > 0)
            .map(([menuId, quantity]) => ({
                menu_id: parseInt(menuId),
                quantity: quantity
            }));
        
        if (menuItems.length === 0) {
            throw new Error('メニューを選択してください');
        }
        
        // ボタンを無効化
        submitBtn.disabled = true;
        submitBtn.textContent = '処理中...';

        // まだPayment Intent / PaymentElementが用意されていなければ初期化だけ行う
        if (!currentPaymentIntent) {
            // Payment Intentを作成して保持
            const paymentIntent = await createPaymentIntent();
            // PaymentElementを初期化（決済方法入力UIを表示）
            await initPaymentElement(paymentIntent.client_secret);
            
            successDiv.textContent = "お支払い情報を入力してから、もう一度「予約する」を押してください。";
            successDiv.style.display = "block";
            return;
        }
        
        // PaymentElementが未初期化の場合は初期化
        if (!elements || !paymentElement) {
            await initPaymentElement(currentPaymentIntent.client_secret);
        }
        
        // Stripe API: PaymentElementを使って決済を実行
        // confirmPaymentは、選択された決済方法に応じて適切なフローを実行する統一API
        const { error: stripeError, paymentIntent: confirmedPaymentIntent } = await stripe.confirmPayment({
            elements,
            // リダイレクトが必要な決済方法の場合のみ自動でリダイレクト
            redirect: "if_required",
        });
        
        if (stripeError) {
            throw new Error(stripeError.message || "決済に失敗しました");
        }
        
        if (!confirmedPaymentIntent || confirmedPaymentIntent.status !== "succeeded") {
            throw new Error("決済が完了していません");
        }
        
        // 予約を作成（Payment Intent IDは作成時に保持したものを使用）
        await createReservation({
            reservation_date: date,
            reservation_time: time,
            number_of_people: numberOfPeople,
            special_requests: specialRequests || null,
            menu_items: menuItems,
            payment_intent_id: currentPaymentIntent.payment_intent_id,
        });
        
        // 成功メッセージを表示
        successDiv.textContent = "予約と決済が完了しました！";
        successDiv.style.display = "block";
        
        // フォームをリセット
        event.target.reset();
        selectedMenuItems = {};
        updateMenuSelection();
        updateSelectedMenuSummary([]);
        currentPaymentIntent = null;
        elements = null;
        paymentElement = null;
        
        // 予約一覧を更新
        await loadReservations();

        // 予約セクションへスクロール（URLフラグメントによる簡易リダイレクト）
        // ユーザー視点では「予約完了画面」に移動したように見える
        if (window.location.hash !== "#reservation") {
            window.location.hash = "reservation";
        }
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = "block";
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '予約する';
    }
}

// 予約一覧を読み込んで表示する関数
async function loadReservations() {
    const reservationsList = document.getElementById("reservations-list");
    if (!reservationsList) return;
    
    try {
        const reservations = await getReservations();
        
        if (reservations.length === 0) {
            reservationsList.innerHTML = "<p class='no-reservations'>予約がありません</p>";
            return;
        }
        
        // 予約一覧をHTMLで生成
        reservationsList.innerHTML = reservations.map(reservation => {
            const date = new Date(reservation.reservation_date);
            const formattedDate = date.toLocaleDateString('ja-JP', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                weekday: 'short'
            });
            
            // メニュー情報を表示
            const menuItemsHtml = reservation.menu_items && reservation.menu_items.length > 0
                ? `<div class="reservation-menu-items">
                    <strong>メニュー:</strong>
                    ${reservation.menu_items.map(item => 
                        `${item.name} × ${item.quantity} (¥${(item.price * item.quantity).toLocaleString()})`
                    ).join(', ')}
                   </div>`
                : '';
            
            const paymentInfoHtml = reservation.amount
                ? `<p class="payment-info">決済金額: ¥${reservation.amount.toLocaleString()} (${getPaymentStatusText(reservation.payment_status)})</p>`
                : '';
            
            return `
                <div class="reservation-item">
                    <div class="reservation-info">
                        <h4>${formattedDate} ${reservation.reservation_time}</h4>
                        <p>人数: ${reservation.number_of_people}名</p>
                        ${menuItemsHtml}
                        ${paymentInfoHtml}
                        ${reservation.special_requests ? `<p class="special-requests">要望: ${reservation.special_requests}</p>` : ''}
                        <p class="reservation-status">ステータス: ${getStatusText(reservation.status)}</p>
                    </div>
                    <button class="btn btn-danger cancel-reservation-btn" data-id="${reservation.id}">
                        キャンセル
                    </button>
                </div>
            `;
        }).join('');
        
        // キャンセルボタンのイベントリスナーを追加
        document.querySelectorAll('.cancel-reservation-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                const reservationId = parseInt(e.currentTarget.dataset.id);
                if (confirm('本当に予約をキャンセルしますか？返金処理も実行されます。')) {
                    try {
                        await cancelReservation(reservationId);
                        await loadReservations();
                    } catch (error) {
                        alert(error.message);
                    }
                }
            });
        });
    } catch (error) {
        reservationsList.innerHTML = `<p class="error">予約の取得に失敗しました: ${error.message}</p>`;
    }
}

// 予約ステータスの日本語テキストを取得する関数
function getStatusText(status) {
    const statusMap = {
        'pending': '保留中',
        'confirmed': '確認済み',
        'cancelled': 'キャンセル済み'
    };
    return statusMap[status] || status;
}

// 決済ステータスの日本語テキストを取得する関数
function getPaymentStatusText(status) {
    const statusMap = {
        'pending': '未決済',
        'succeeded': '決済完了',
        'refunded': '返金済み'
    };
    return statusMap[status] || status;
}

// 初期化関数
async function initReservationUI() {
    const reservationForm = document.getElementById("reservation-form");
    if (reservationForm) {
        reservationForm.addEventListener("submit", handleReservationSubmit);
    }
    
    // メニュー選択UIを読み込む
    await loadMenuSelection();
    
    // Stripe公開可能キーを取得して初期化
    try {
        const keyResponse = await fetch(`${API_BASE_URL}/api/stripe/publishable-key`);
        if (keyResponse.ok) {
            const keyData = await keyResponse.json();
            initStripe(keyData.publishable_key);
        }
    } catch (error) {
        console.error("Stripe公開可能キーの取得に失敗しました:", error);
    }
    
    // ログイン状態を確認してから予約一覧を読み込む
    const user = await getCurrentUser();
    if (user) {
        try {
            await loadReservations();
            // 定期的に予約一覧を更新（30秒ごと）
            setInterval(async () => {
                try {
                    await loadReservations();
                } catch (error) {
                    console.error("予約一覧の更新に失敗しました:", error);
                }
            }, 30000);
        } catch (error) {
            console.error("予約一覧の読み込みに失敗しました:", error);
        }
    }
}

// DOMContentLoadedイベントで初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReservationUI);
} else {
    initReservationUI();
}

// 他のモジュールから使用できるようにエクスポート
export { loadReservations };
