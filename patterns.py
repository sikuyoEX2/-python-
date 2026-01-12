"""
ローソク足パターン判定モジュール
ピンバー、包み足などの検出
"""
import pandas as pd
import numpy as np
from typing import Tuple


def calculate_candle_metrics(row: pd.Series) -> dict:
    """
    ローソク足の各部分のサイズを計算
    
    Args:
        row: OHLCデータを含む1行
    
    Returns:
        各部分のサイズを含む辞書
    """
    open_price = row['open']
    high = row['high']
    low = row['low']
    close = row['close']
    
    body = abs(close - open_price)
    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low
    total_range = high - low
    
    return {
        'body': body,
        'upper_wick': upper_wick,
        'lower_wick': lower_wick,
        'total_range': total_range,
        'is_bullish': close > open_price,
        'is_bearish': close < open_price
    }


def is_pin_bar(row: pd.Series, wick_ratio: float = 2.0) -> Tuple[bool, str]:
    """
    ピンバー（上ヒゲ/下ヒゲ）を判定
    
    Args:
        row: OHLCデータを含む1行
        wick_ratio: ヒゲが実体の何倍以上でピンバーとするか
    
    Returns:
        (ピンバーかどうか, タイプ "bullish_pin"/"bearish_pin"/"none")
    """
    metrics = calculate_candle_metrics(row)
    
    if metrics['body'] == 0:
        return False, "none"
    
    # 下ヒゲピンバー（買いシグナル）: 下ヒゲが実体の2倍以上、上ヒゲは小さい
    if (metrics['lower_wick'] >= metrics['body'] * wick_ratio and 
        metrics['upper_wick'] < metrics['body'] * 0.5):
        return True, "bullish_pin"
    
    # 上ヒゲピンバー（売りシグナル）: 上ヒゲが実体の2倍以上、下ヒゲは小さい
    if (metrics['upper_wick'] >= metrics['body'] * wick_ratio and 
        metrics['lower_wick'] < metrics['body'] * 0.5):
        return True, "bearish_pin"
    
    return False, "none"


def is_engulfing(current: pd.Series, previous: pd.Series) -> Tuple[bool, str]:
    """
    包み足（つつみ線）を判定
    
    Args:
        current: 現在のローソク足
        previous: 1つ前のローソク足
    
    Returns:
        (包み足かどうか, タイプ "bullish_engulfing"/"bearish_engulfing"/"none")
    """
    curr_open = current['open']
    curr_close = current['close']
    prev_open = previous['open']
    prev_close = previous['close']
    
    curr_body_high = max(curr_open, curr_close)
    curr_body_low = min(curr_open, curr_close)
    prev_body_high = max(prev_open, prev_close)
    prev_body_low = min(prev_open, prev_close)
    
    # 陽線の包み足（買いシグナル）: 前日陰線を当日陽線が包む
    if (prev_close < prev_open and  # 前日が陰線
        curr_close > curr_open and  # 当日が陽線
        curr_body_low <= prev_body_low and  # 当日の安値が前日実体より低い
        curr_body_high >= prev_body_high):  # 当日の高値が前日実体より高い
        return True, "bullish_engulfing"
    
    # 陰線の包み足（売りシグナル）: 前日陽線を当日陰線が包む
    if (prev_close > prev_open and  # 前日が陽線
        curr_close < curr_open and  # 当日が陰線
        curr_body_low <= prev_body_low and
        curr_body_high >= prev_body_high):
        return True, "bearish_engulfing"
    
    return False, "none"


def detect_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameにパターン検出結果を追加
    
    Args:
        df: OHLCデータを含むDataFrame
    
    Returns:
        パターン列が追加されたDataFrame
    """
    df = df.copy()
    
    # 初期化
    df['pin_bar'] = "none"
    df['engulfing'] = "none"
    
    for i in range(1, len(df)):
        # ピンバー判定
        is_pin, pin_type = is_pin_bar(df.iloc[i])
        df.iloc[i, df.columns.get_loc('pin_bar')] = pin_type
        
        # 包み足判定
        is_eng, eng_type = is_engulfing(df.iloc[i], df.iloc[i-1])
        df.iloc[i, df.columns.get_loc('engulfing')] = eng_type
    
    return df
