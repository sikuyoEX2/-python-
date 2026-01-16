
import yfinance as yf
import json

tickers = ["7203.T", "9984.T", "6758.T"]  # トヨタ, ソフトバンクG, ソニー

print("Testing yfinance news fetching for Japanese stocks...")

for ticker in tickers:
    print(f"\n--- {ticker} ---")
    try:
        t = yf.Ticker(ticker)
        news = t.news
        if news:
            print(f"Found {len(news)} news items.")
            for n in news[:2]:
                print(f"- {n.get('title')} ({n.get('publisher')})")
        else:
            print("No news found.")
            
            # 検索APIも試してみる（yfinanceのバージョンによる）
            try:
                print("Trying search...")
                # newsが空の場合のフォールバック動作確認
                pass
            except:
                pass
            
    except Exception as e:
        print(f"Error: {e}")
