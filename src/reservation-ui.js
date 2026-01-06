// 予約UI（予約フォーム・予約一覧）を管理するJavaScriptモジュール

import { createReservation, getReservations, cancelReservation } from "./reservation.js";
import { getCurrentUser } from "./auth.js";

// 予約フォームの送信処理
async function handleReservationSubmit(event) {
    event.preventDefault();
    
    const date = document.getElementById("reservation-date").value;
    const time = document.getElementById("reservation-time").value;
    const numberOfPeople = parseInt(document.getElementById("reservation-people").value);
    const specialRequests = document.getElementById("reservation-requests").value;
    const errorDiv = document.getElementById("reservation-error");
    const successDiv = document.getElementById("reservation-success");
    
    try {
        errorDiv.textContent = "";
        errorDiv.style.display = "none";
        successDiv.textContent = "";
        successDiv.style.display = "none";
        
        await createReservation({
            reservation_date: date,
            reservation_time: time,
            number_of_people: numberOfPeople,
            special_requests: specialRequests || null,
        });
        
        // 成功メッセージを表示
        successDiv.textContent = "予約が完了しました！";
        successDiv.style.display = "block";
        
        // フォームをリセット
        event.target.reset();
        
        // 予約一覧を更新
        await loadReservations();
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = "block";
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
        
        // 予約一覧をHTMLで生成。mapは値のマッピングを行う関数。reservation => HTML文字列
        reservationsList.innerHTML = reservations.map(reservation => {
            const date = new Date(reservation.reservation_date);
            const formattedDate = date.toLocaleDateString('ja-JP', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                weekday: 'short'
            });
            
            return `
                <div class="reservation-item">
                    <div class="reservation-info">
                        <h4>${formattedDate} ${reservation.reservation_time}</h4>
                        <p>人数: ${reservation.number_of_people}名</p>
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
                // e.currentTargetを使用することで、ボタン要素自体を確実に取得できる
                const reservationId = parseInt(e.currentTarget.dataset.id);
                console.log(reservationId);
                if (confirm('本当に予約をキャンセルしますか？')) {
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

// 初期化関数
async function initReservationUI() {
    const reservationForm = document.getElementById("reservation-form");
    if (reservationForm) {
        reservationForm.addEventListener("submit", handleReservationSubmit);
    }
    
    // ログイン状態を確認してから予約一覧を読み込む。ここはセッション (token) が有効な場合に実行され、意味を持つ。
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

