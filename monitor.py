"""
株価シグナル監視スクリプト（GitHub Actions用）
定期実行してシグナルを検出し、通知を送信
"""
import os
import sys
import requests
from datetime import datetime

# 環境変数から設定を取得
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

# 監視対象銘柄（カンマ区切り）
WATCHLIST = os.getenv("WATCHLIST", "AAPL,NVDA,GOOGL").split(",")


def send_discord_notification(ticker: str, signal_type: str, message: str, 
                               entry: float = None, stop_loss: float = None, take_profit: float = None):
    """Discord通知を送信"""
    if not DISCORD_WEBHOOK_URL:
        print("Discord Webhook URLが設定されていません")
        return False
    
    color = 0x00FF00 if signal_type == "buy" else 0xFF0000
    emoji = "🟢" if signal_type == "buy" else "🔴"
    signal_name = "買いシグナル" if signal_type == "buy" else "売りシグナル"
    
    embed = {
        "title": f"{emoji} {ticker} - {signal_name}",
        "description": message,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "fields": []
    }
    
    if entry is not None:
        embed["fields"].append({"name": "エントリー", "value": f"{entry:.2f}", "inline": True})
    if stop_loss is not None:
        embed["fields"].append({"name": "損切り", "value": f"{stop_loss:.2f}", "inline": True})
    if take_profit is not None:
        embed["fields"].append({"name": "利確目標", "value": f"{take_profit:.2f}", "inline": True})
    
    embed["footer"] = {"text": "Stock Signal Monitor (GitHub Actions)"}
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code == 204
    except Exception as e:
        print(f"Discord通知エラー: {e}")
        return False


def check_signal(ticker: str) -> dict:
    """銘柄のシグナルをチェック"""
    try:
        import yfinance as yf
        import pandas as pd
        
        # データ取得
        stock = yf.Ticker(ticker)
        df_15m = stock.history(period="5d", interval="15m")
        df_1h = stock.history(period="1mo", interval="1h")
        
        if df_15m.empty or df_1h.empty:
            return {"signal": None}
        
        # カラム名を小文字に
        df_15m.columns = [c.lower() for c in df_15m.columns]
        df_1h.columns = [c.lower() for c in df_1h.columns]
        
        # 4時間足に変換
        df_4h = df_1h.resample('4h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        
        # EMA計算
        for df in [df_15m, df_4h]:
            df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta).where(delta < 0, 0.0)
            avg_gain = gain.ewm(span=14, adjust=False).mean()
            avg_loss = loss.ewm(span=14, adjust=False).mean()
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
        
        # 最新データ
        latest = df_15m.iloc[-1]
        prev = df_15m.iloc[-2]
        latest_4h = df_4h.iloc[-1]
        
        # トレンド判定
        main_uptrend = latest['close'] > latest['ema_200']
        higher_uptrend = latest_4h['close'] > latest_4h['ema_200']
        main_downtrend = latest['close'] < latest['ema_200']
        higher_downtrend = latest_4h['close'] < latest_4h['ema_200']
        
        # ピンバー検出（簡易版）
        body = abs(latest['close'] - latest['open'])
        lower_wick = min(latest['open'], latest['close']) - latest['low']
        upper_wick = latest['high'] - max(latest['open'], latest['close'])
        
        bullish_pin = body > 0 and lower_wick >= body * 2 and upper_wick < body * 0.5
        bearish_pin = body > 0 and upper_wick >= body * 2 and lower_wick < body * 0.5
        
        # 包み足検出
        curr_body_high = max(latest['open'], latest['close'])
        curr_body_low = min(latest['open'], latest['close'])
        prev_body_high = max(prev['open'], prev['close'])
        prev_body_low = min(prev['open'], prev['close'])
        
        bullish_engulfing = (prev['close'] < prev['open'] and 
                             latest['close'] > latest['open'] and
                             curr_body_low <= prev_body_low and 
                             curr_body_high >= prev_body_high)
        
        bearish_engulfing = (prev['close'] > prev['open'] and 
                             latest['close'] < latest['open'] and
                             curr_body_low <= prev_body_low and 
                             curr_body_high >= prev_body_high)
        
        # シグナル判定
        signal_type = None
        trigger = ""
        
        # 買いシグナル
        if main_uptrend and higher_uptrend:
            near_ema = abs(latest['close'] - latest['ema_20']) / latest['ema_20'] < 0.01
            rsi_ok = latest['rsi'] < 40
            if near_ema or rsi_ok:
                if bullish_pin:
                    signal_type = "buy"
                    trigger = "下ヒゲピンバー"
                elif bullish_engulfing:
                    signal_type = "buy"
                    trigger = "陽線包み足"
        
        # 売りシグナル
        if main_downtrend and higher_downtrend:
            near_ema = abs(latest['close'] - latest['ema_20']) / latest['ema_20'] < 0.01
            rsi_ok = latest['rsi'] > 60
            if near_ema or rsi_ok:
                if bearish_pin:
                    signal_type = "sell"
                    trigger = "上ヒゲピンバー"
                elif bearish_engulfing:
                    signal_type = "sell"
                    trigger = "陰線包み足"
        
        if signal_type:
            # リスクリワード計算
            recent = df_15m.tail(10)
            current_price = latest['close']
            
            if signal_type == "buy":
                stop_loss = recent['low'].min()
                risk = current_price - stop_loss
                take_profit = current_price + (risk * 2)
            else:
                stop_loss = recent['high'].max()
                risk = stop_loss - current_price
                take_profit = current_price - (risk * 2)
            
            return {
                "signal": signal_type,
                "trigger": trigger,
                "entry": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
        
        return {"signal": None}
        
    except Exception as e:
        print(f"シグナルチェックエラー ({ticker}): {e}")
        return {"signal": None}


def main():
    """メイン処理"""
    print(f"=== 株価シグナル監視 ({datetime.now().isoformat()}) ===")
    print(f"監視銘柄: {WATCHLIST}")
    
    signals_found = 0
    
    for ticker in WATCHLIST:
        ticker = ticker.strip().upper()
        if not ticker:
            continue
        
        print(f"\n{ticker} をチェック中...")
        result = check_signal(ticker)
        
        if result.get("signal"):
            signals_found += 1
            message = f"トリガー: {result['trigger']}"
            
            print(f"  → シグナル検出！ {result['signal'].upper()}")
            
            success = send_discord_notification(
                ticker=ticker,
                signal_type=result["signal"],
                message=message,
                entry=result.get("entry"),
                stop_loss=result.get("stop_loss"),
                take_profit=result.get("take_profit")
            )
            
            if success:
                print(f"  → Discord通知送信完了")
            else:
                print(f"  → Discord通知送信失敗")
        else:
            print(f"  → シグナルなし")
    
    print(f"\n=== 完了: {signals_found}件のシグナル検出 ===")


if __name__ == "__main__":
    main()
