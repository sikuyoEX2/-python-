"""
テクニカル指標計算モジュール
EMA, RSI などの計算
"""
import pandas as pd
import numpy as np


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    指数移動平均（EMA）を計算
    
    Args:
        series: 価格データ（通常は終値）
        period: EMA期間
    
    Returns:
        EMA値のSeries
    """
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI（相対力指数）を計算
    
    Args:
        series: 価格データ（通常は終値）
        period: RSI期間（デフォルト: 14）
    
    Returns:
        RSI値のSeries（0-100の範囲）
    """
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameにすべてのテクニカル指標を追加
    
    Args:
        df: OHLCデータを含むDataFrame
    
    Returns:
        指標が追加されたDataFrame
    """
    df = df.copy()
    
    # EMA
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['ema_200'] = calculate_ema(df['close'], 200)
    
    # RSI
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    # 20EMAからの乖離率（%）
    df['ema_20_distance'] = ((df['close'] - df['ema_20']) / df['ema_20']) * 100
    
    return df


def is_near_ema20(row: pd.Series, threshold: float = 0.5) -> bool:
    """
    価格が20EMA付近にあるかを判定
    
    Args:
        row: DataFrameの1行
        threshold: 乖離率の閾値（%）
    
    Returns:
        20EMA付近にあればTrue
    """
    return abs(row['ema_20_distance']) <= threshold
