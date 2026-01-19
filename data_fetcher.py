"""
データ取得モジュール（最適化版）
yfinanceをキャッシュ付きで使用してAPIコール削減
"""
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict


# キャッシュのTTL（秒）
CACHE_TTL_SECONDS = 300  # 5分


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_stock_data(
    ticker: str,
    interval: str = "15m",
    period: str = "5d"
) -> pd.DataFrame:
    """
    指定した銘柄のOHLCデータを取得（キャッシュ付き）
    
    Args:
        ticker: 銘柄コード（例: "AAPL", "7203.T"）
        interval: 時間足（"1m", "5m", "15m", "1h", "4h", "1d"など）
        period: 取得期間（"1d", "5d", "1mo", "3mo"など）
    
    Returns:
        OHLCデータを含むDataFrame
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            raise ValueError(f"データが取得できませんでした: {ticker}")
        
        # カラム名を標準化
        df.columns = [col.lower() for col in df.columns]
        
        return df
    except Exception as e:
        raise Exception(f"データ取得エラー ({ticker}): {str(e)}")


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_multi_timeframe_data(
    ticker: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    マルチタイムフレームデータを取得（メイン足: 15分、上位足: 4時間）
    
    Args:
        ticker: 銘柄コード
    
    Returns:
        (メイン足データ, 上位足データ) のタプル
    
    Note:
        yfinanceの制限:
        - 15分足: 最大60日分
        - 4時間足は直接取得不可のため1時間足を4本集約して生成
    """
    # メイン足（15分足）: 直近5日分
    df_15m = fetch_stock_data(ticker, interval="15m", period="5d")
    
    # 上位足（4時間足）: 1時間足を取得して4本ごとに集約
    df_1h = fetch_stock_data(ticker, interval="1h", period="1mo")
    df_4h = resample_to_4h(df_1h)
    
    return df_15m, df_4h


def resample_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    """
    1時間足データを4時間足に変換
    
    Args:
        df_1h: 1時間足のOHLCデータ
    
    Returns:
        4時間足に集約されたDataFrame
    """
    df_4h = df_1h.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return df_4h


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_ticker_info(ticker: str) -> dict:
    """
    銘柄の基本情報を取得（キャッシュ付き、タイムアウト対応）
    
    Args:
        ticker: 銘柄コード
    
    Returns:
        銘柄情報の辞書
    """
    import concurrent.futures
    
    def fetch_info():
        stock = yf.Ticker(ticker)
        return stock.info
    
    try:
        # 10秒タイムアウト
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fetch_info)
            info = future.result(timeout=10)
            
        return {
            "name": info.get("shortName", ticker),
            "currency": info.get("currency", "Unknown"),
            "exchange": info.get("exchange", "Unknown"),
            "current_price": info.get("regularMarketPrice") or info.get("currentPrice")
        }
    except concurrent.futures.TimeoutError:
        return {"name": ticker, "currency": "Unknown", "exchange": "Unknown", "current_price": None}
    except:
        return {"name": ticker, "currency": "Unknown", "exchange": "Unknown", "current_price": None}


@st.cache_data(ttl=60)  # 1分キャッシュ
def get_current_price(ticker: str) -> Optional[float]:
    """現在価格を取得（キャッシュ付き）"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get('regularMarketPrice') or info.get('currentPrice')
    except:
        return None


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_stock_data_batch(tickers: tuple, max_price: float = 10000) -> Dict:
    """
    複数銘柄のデータを一括取得（スクリーナー用）
    
    Args:
        tickers: 銘柄コードのタプル（キャッシュのためタプルを使用）
        max_price: 最大株価フィルター
    
    Returns:
        銘柄データの辞書
    """
    results = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get('regularMarketPrice') or info.get('currentPrice')
            
            if price and price <= max_price:
                results[ticker] = {
                    'ticker': ticker,
                    'name': info.get('shortName', ticker),
                    'price': price,
                    'info': info
                }
        except:
            continue
    
    return results


def clear_cache():
    """全てのキャッシュをクリア"""
    st.cache_data.clear()
