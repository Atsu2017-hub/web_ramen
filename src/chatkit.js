async function getChatKitSessionToken() {
  const apiBase =
    window.location.hostname === "localhost" && window.location.port === "8080"
      ? ""
      : "http://localhost:8000";

  const response = await fetch(`${apiBase}/api/chatkit/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const { client_secret } = await response.json();
  return client_secret;
}


// ChatKitの初期化
async function initChatKit() {
  const chatkit = document.getElementById('my-chat');
  
  if (!chatkit) {
    console.error('ChatKit element not found');
    return;
  }

  // ChatKitのオプションを設定。
  chatkit.setOptions({
    api: {
      async getClientSecret(currentClientSecret) {
        if (!currentClientSecret) {
          const client_secret = await getChatKitSessionToken();
          return client_secret;
        }
        // セッションをリフレッシュ
        const clientSecret = await getChatKitSessionToken();
        return clientSecret;
      }
    },
    theme: {
      colorScheme: "dark", // 全体の色。
      color: { 
        accent: { // 送信ボタンの色
          primary: "#a9a9a9", 
          level: 0
        }
      },
      radius: "round", // メッセージボックスと送信ボタンの丸み
      density: "compact", // メッセージボックスと送信ボタンの密度
      typography: { 
        fontFamily: "'Inter', sans-serif" 
      },
    },
    composer: {
      placeholder: "なんか打てやがれ",
    },
    startScreen: {
      greeting: "なんでも質問しやがれ"
    },
    widgets: { // widgetの handler="client" とすると onAction がコールバックされる。
      async onAction(action, item) {
        try {
          const apiBase =
            window.location.hostname === "localhost" && window.location.port === "8080"
              ? ""
              : "http://localhost:8000";

          console.log('onAction called', action, item);
          const response = await fetch(`${apiBase}/api/widget-action`, { // responseも後で実装する
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, itemId: item.id }), //actionはaction: actionの省略記法。オブジェクトをJSON化
          });
          
          if (!response.ok) {
            console.error('Response not OK:', response.status, response.statusText);
            return;
          }
          
          const data = await response.json();
          console.log(data);
          
          if(data.response === "hour"){
            await chatkit.sendUserMessage({ text: "営業時間は？" });
          }
          else if(data.response === "pay"){
            await chatkit.sendUserMessage({ text: "支払い方法は？" });
          }else if(data.response === "exist"){
            await chatkit.sendUserMessage({ text: "駐車場はありますか？" });
          }else{
            console.log("NG");
          }
        } catch (error) {
          console.error('Error in onAction:', error);
        }
      },
    },
  });
} 


// DOMContentLoadedイベントで初期化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initChatKit);
} else {
  initChatKit();
}

