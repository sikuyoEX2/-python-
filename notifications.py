"""
通知モジュール
Web画面アラート、ブラウザ通知、Webhook（LINE/Discord）対応
"""
import streamlit as st
from typing import Optional
from datetime import datetime
import requests
import json


class NotificationManager:
    """通知管理クラス"""
    
    def __init__(self):
        self.history = []
    
    def add_alert(self, ticker: str, signal_type: str, message: str):
        """
        アラートを追加
        
        Args:
            ticker: 銘柄コード
            signal_type: シグナルタイプ（"buy", "sell", "info"）
            message: 通知メッセージ
        """
        alert = {
            "timestamp": datetime.now(),
            "ticker": ticker,
            "type": signal_type,
            "message": message
        }
        self.history.insert(0, alert)
        
        # 履歴は最新50件まで保持
        if len(self.history) > 50:
            self.history = self.history[:50]
    
    def show_web_alert(self, signal_type: str, message: str):
        """
        Streamlit上でアラートを表示
        
        Args:
            signal_type: シグナルタイプ
            message: 表示メッセージ
        """
        if signal_type == "buy":
            st.success(f"🟢 {message}")
        elif signal_type == "sell":
            st.error(f"🔴 {message}")
        else:
            st.info(f"ℹ️ {message}")
    
    def get_history(self, limit: int = 10) -> list:
        """
        通知履歴を取得
        
        Args:
            limit: 取得件数
        
        Returns:
            通知履歴のリスト
        """
        return self.history[:limit]


class WebhookNotifier:
    """Webhook通知クラス（Discord/LINE対応）"""
    
    def __init__(self, discord_url: str = None, line_token: str = None):
        self.discord_url = discord_url
        self.line_token = line_token
    
    def send_discord(self, ticker: str, signal_type: str, message: str, 
                     entry: float = None, stop_loss: float = None, take_profit: float = None) -> bool:
        """
        Discord Webhookに通知を送信
        
        Args:
            ticker: 銘柄コード
            signal_type: "buy" or "sell"
            message: シグナルメッセージ
            entry: エントリー価格
            stop_loss: 損切り価格
            take_profit: 利確価格
        
        Returns:
            送信成功したか
        """
        if not self.discord_url:
            return False
        
        try:
            # Embed形式でリッチな通知を作成
            color = 0x00FF00 if signal_type == "buy" else 0xFF0000  # 緑 or 赤
            emoji = "🟢" if signal_type == "buy" else "🔴"
            signal_name = "買いシグナル" if signal_type == "buy" else "売りシグナル"
            
            embed = {
                "title": f"{emoji} {ticker} - {signal_name}",
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "fields": []
            }
            
            # リスクリワード情報があれば追加
            if entry is not None:
                embed["fields"].append({"name": "エントリー", "value": f"{entry:.2f}", "inline": True})
            if stop_loss is not None:
                embed["fields"].append({"name": "損切り", "value": f"{stop_loss:.2f}", "inline": True})
            if take_profit is not None:
                embed["fields"].append({"name": "利確目標", "value": f"{take_profit:.2f}", "inline": True})
            
            payload = {"embeds": [embed]}
            
            response = requests.post(
                self.discord_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 204
            
        except Exception as e:
            print(f"Discord通知エラー: {e}")
            return False
    
    def send_line(self, ticker: str, signal_type: str, message: str,
                  entry: float = None, stop_loss: float = None, take_profit: float = None) -> bool:
        """
        LINE Notifyに通知を送信
        
        Args:
            ticker: 銘柄コード
            signal_type: "buy" or "sell"
            message: シグナルメッセージ
            entry: エントリー価格
            stop_loss: 損切り価格
            take_profit: 利確価格
        
        Returns:
            送信成功したか
        """
        if not self.line_token:
            return False
        
        try:
            emoji = "🟢" if signal_type == "buy" else "🔴"
            signal_name = "買いシグナル" if signal_type == "buy" else "売りシグナル"
            
            text = f"\n{emoji} {ticker} - {signal_name}\n{message}"
            
            if entry is not None:
                text += f"\n\n📊 リスクリワード"
                text += f"\nエントリー: {entry:.2f}"
            if stop_loss is not None:
                text += f"\n損切り: {stop_loss:.2f}"
            if take_profit is not None:
                text += f"\n利確目標: {take_profit:.2f}"
            
            headers = {"Authorization": f"Bearer {self.line_token}"}
            payload = {"message": text}
            
            response = requests.post(
                "https://notify-api.line.me/api/notify",
                headers=headers,
                data=payload,
                timeout=10
            )
            return response.status_code == 200
            
        except Exception as e:
            print(f"LINE通知エラー: {e}")
            return False
    
    def send_all(self, ticker: str, signal_type: str, message: str, **kwargs) -> dict:
        """
        設定されている全てのWebhookに通知を送信
        
        Returns:
            各サービスの送信結果
        """
        results = {
            "discord": self.send_discord(ticker, signal_type, message, **kwargs),
            "line": self.send_line(ticker, signal_type, message, **kwargs)
        }
        return results


def render_notification_settings():
    """
    通知設定UIをレンダリング（Streamlitサイドバー用）
    """
    st.subheader("🔔 通知設定")
    
    # セッション状態の初期化
    if 'discord_webhook' not in st.session_state:
        st.session_state.discord_webhook = ""
    if 'line_token' not in st.session_state:
        st.session_state.line_token = ""
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'refresh_interval' not in st.session_state:
        st.session_state.refresh_interval = 60
    
    with st.expander("⚙️ Webhook設定", expanded=False):
        # Discord設定
        st.session_state.discord_webhook = st.text_input(
            "Discord Webhook URL",
            value=st.session_state.discord_webhook,
            type="password",
            help="Discord > サーバー設定 > 連携サービス > ウェブフック で取得"
        )
        
        # LINE設定
        st.session_state.line_token = st.text_input(
            "LINE Notify トークン",
            value=st.session_state.line_token,
            type="password",
            help="https://notify-bot.line.me/ で取得"
        )
        
        # テスト送信ボタン
        if st.button("📤 テスト通知を送信"):
            notifier = WebhookNotifier(
                discord_url=st.session_state.discord_webhook or None,
                line_token=st.session_state.line_token or None
            )
            results = notifier.send_all("TEST", "buy", "テスト通知です")
            
            if results["discord"]:
                st.success("✓ Discord送信成功")
            elif st.session_state.discord_webhook:
                st.error("✗ Discord送信失敗")
            
            if results["line"]:
                st.success("✓ LINE送信成功")
            elif st.session_state.line_token:
                st.error("✗ LINE送信失敗")
    
    # 自動更新設定
    with st.expander("🔄 自動更新設定", expanded=False):
        st.session_state.auto_refresh = st.checkbox(
            "自動更新を有効にする",
            value=st.session_state.auto_refresh
        )
        
        if st.session_state.auto_refresh:
            st.session_state.refresh_interval = st.slider(
                "更新間隔（秒）",
                min_value=30,
                max_value=300,
                value=st.session_state.refresh_interval,
                step=30
            )
            st.caption(f"⏱ {st.session_state.refresh_interval}秒ごとに自動更新")


def get_webhook_notifier() -> WebhookNotifier:
    """
    現在の設定からWebhookNotifierインスタンスを取得
    """
    return WebhookNotifier(
        discord_url=st.session_state.get('discord_webhook') or None,
        line_token=st.session_state.get('line_token') or None
    )


def get_browser_notification_script(ticker: str, signal_type: str, message: str) -> str:
    """
    ブラウザのデスクトップ通知を表示するJavaScript
    
    Args:
        ticker: 銘柄コード
        signal_type: "buy" or "sell"
        message: 通知メッセージ
    
    Returns:
        実行するJavaScriptコード
    """
    title = f"{'🟢 買い' if signal_type == 'buy' else '🔴 売り'}シグナル - {ticker}"
    
    script = f"""
    <script>
    if ("Notification" in window) {{
        if (Notification.permission === "granted") {{
            new Notification("{title}", {{
                body: "{message}",
                icon: "📈"
            }});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(function (permission) {{
                if (permission === "granted") {{
                    new Notification("{title}", {{
                        body: "{message}",
                        icon: "📈"
                    }});
                }}
            }});
        }}
    }}
    </script>
    """
    return script
