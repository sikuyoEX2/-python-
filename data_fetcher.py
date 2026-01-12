"""
データ取得モジュール
yfinanceを使用してマルチタイムフレームの株価データを取得
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional


def fetch_stock_data(
    ticker: str,
    interval: str = "15m",
    period: str = "5d"
) -> pd.DataFrame:
    """
    指定した銘柄のOHLCデータを取得
    
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


def get_ticker_info(ticker: str) -> dict:
    """
    銘柄の基本情報を取得
    
    Args:
        ticker: 銘柄コード
    
    Returns:
        銘柄情報の辞書
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "name": info.get("shortName", ticker),
            "currency": info.get("currency", "Unknown"),
            "exchange": info.get("exchange", "Unknown"),
            "current_price": info.get("regularMarketPrice", None)
        }
    except:
        return {"name": ticker, "currency": "Unknown", "exchange": "Unknown", "current_price": None}
