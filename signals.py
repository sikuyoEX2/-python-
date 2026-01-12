"""
シグナル判定モジュール
環境認識・セットアップ・トリガーの3段階判定
"""
import pandas as pd
from typing import Tuple, Optional
from indicators import add_indicators, is_near_ema20
from patterns import detect_patterns


class TrendState:
    """トレンド状態を表すクラス"""
    UPTREND = "上昇トレンド"
    DOWNTREND = "下落トレンド"
    NEUTRAL = "レンジ"


class SignalType:
    """シグナルタイプ"""
    LONG = "買いシグナル"
    SHORT = "売りシグナル"
    NONE = "様子見"


def analyze_trend(df: pd.DataFrame) -> str:
    """
    トレンドを分析（終値と200EMAの関係）
    
    Args:
        df: 指標が追加されたDataFrame
    
    Returns:
        トレンド状態
    """
    if df.empty or 'ema_200' not in df.columns:
        return TrendState.NEUTRAL
    
    latest = df.iloc[-1]
    
    if pd.isna(latest['ema_200']):
        return TrendState.NEUTRAL
    
    if latest['close'] > latest['ema_200']:
        return TrendState.UPTREND
    elif latest['close'] < latest['ema_200']:
        return TrendState.DOWNTREND
    else:
        return TrendState.NEUTRAL


def check_environment(df_main: pd.DataFrame, df_higher: pd.DataFrame) -> Tuple[bool, bool, str]:
    """
    環境認識: 上位足とメイン足のトレンド確認
    
    Args:
        df_main: メイン時間足データ
        df_higher: 上位時間足データ
    
    Returns:
        (買い環境か, 売り環境か, トレンド説明)
    """
    main_trend = analyze_trend(df_main)
    higher_trend = analyze_trend(df_higher)
    
    # 両方上昇トレンド → 買い環境
    long_env = (main_trend == TrendState.UPTREND and higher_trend == TrendState.UPTREND)
    
    # 両方下落トレンド → 売り環境
    short_env = (main_trend == TrendState.DOWNTREND and higher_trend == TrendState.DOWNTREND)
    
    trend_desc = f"メイン足: {main_trend} / 上位足: {higher_trend}"
    
    return long_env, short_env, trend_desc


def check_setup(row: pd.Series, is_long: bool) -> bool:
    """
    セットアップ条件を確認
    
    Args:
        row: 現在のローソク足データ
        is_long: ロング（買い）セットアップを確認するか
    
    Returns:
        セットアップ条件を満たしているか
    """
    near_ema = is_near_ema20(row, threshold=1.0)
    
    if is_long:
        # 買いセットアップ: 20EMA付近まで下落 or RSI < 40
        rsi_condition = row['rsi'] < 40 if pd.notna(row['rsi']) else False
        return near_ema or rsi_condition
    else:
        # 売りセットアップ: 20EMA付近まで上昇 or RSI > 60
        rsi_condition = row['rsi'] > 60 if pd.notna(row['rsi']) else False
        return near_ema or rsi_condition


def check_trigger(row: pd.Series, is_long: bool) -> Tuple[bool, str]:
    """
    トリガー条件を確認（ローソク足パターン）
    
    Args:
        row: 現在のローソク足データ
        is_long: ロング（買い）トリガーを確認するか
    
    Returns:
        (トリガー発生か, トリガーの説明)
    """
    pin_bar = row.get('pin_bar', 'none')
    engulfing = row.get('engulfing', 'none')
    
    if is_long:
        # 買いトリガー: 下ヒゲピンバー or 陽線包み足
        if pin_bar == "bullish_pin":
            return True, "下ヒゲピンバー"
        if engulfing == "bullish_engulfing":
            return True, "陽線包み足"
    else:
        # 売りトリガー: 上ヒゲピンバー or 陰線包み足
        if pin_bar == "bearish_pin":
            return True, "上ヒゲピンバー"
        if engulfing == "bearish_engulfing":
            return True, "陰線包み足"
    
    return False, ""


def calculate_risk_reward(
    df: pd.DataFrame,
    is_long: bool,
    lookback: int = 10,
    rr_ratio: float = 2.0
) -> dict:
    """
    リスクリワードを計算
    
    Args:
        df: OHLCデータ
        is_long: ロングポジションか
        lookback: 損切りライン検出に使う過去足数
        rr_ratio: 目標リスクリワード比率
    
    Returns:
        エントリー、損切り、利確の価格情報
    """
    if len(df) < lookback:
        lookback = len(df)
    
    recent = df.tail(lookback)
    current_price = df.iloc[-1]['close']
    
    if is_long:
        # 買いの場合: 直近安値を損切りライン
        stop_loss = recent['low'].min()
        risk = current_price - stop_loss
        take_profit = current_price + (risk * rr_ratio)
    else:
        # 売りの場合: 直近高値を損切りライン
        stop_loss = recent['high'].max()
        risk = stop_loss - current_price
        take_profit = current_price - (risk * rr_ratio)
    
    return {
        "entry": current_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk": abs(risk),
        "reward": abs(risk * rr_ratio),
        "rr_ratio": rr_ratio
    }


def generate_signal(
    df_main: pd.DataFrame,
    df_higher: pd.DataFrame
) -> dict:
    """
    総合的なシグナルを生成
    
    Args:
        df_main: メイン時間足データ（指標・パターン追加済み）
        df_higher: 上位時間足データ（指標追加済み）
    
    Returns:
        シグナル情報を含む辞書
    """
    result = {
        "signal": SignalType.NONE,
        "trend": "",
        "setup": False,
        "trigger": "",
        "risk_reward": None,
        "current_state": "様子見",
        "details": []
    }
    
    if df_main.empty or df_higher.empty:
        return result
    
    # 1. 環境認識
    long_env, short_env, trend_desc = check_environment(df_main, df_higher)
    result["trend"] = trend_desc
    
    current = df_main.iloc[-1]
    
    # 2. セットアップ確認
    if long_env:
        result["details"].append("✓ 上昇トレンド環境")
        setup_ok = check_setup(current, is_long=True)
        if setup_ok:
            result["setup"] = True
            result["details"].append("✓ 押し目ゾーン（20EMA付近 or RSI<40）")
            result["current_state"] = "押し目待ち"
            
            # 3. トリガー確認
            trigger_ok, trigger_desc = check_trigger(current, is_long=True)
            if trigger_ok:
                result["signal"] = SignalType.LONG
                result["trigger"] = trigger_desc
                result["details"].append(f"✓ トリガー発生: {trigger_desc}")
                result["current_state"] = "🟢 買いシグナル点灯"
                result["risk_reward"] = calculate_risk_reward(df_main, is_long=True)
    
    elif short_env:
        result["details"].append("✓ 下落トレンド環境")
        setup_ok = check_setup(current, is_long=False)
        if setup_ok:
            result["setup"] = True
            result["details"].append("✓ 戻りゾーン（20EMA付近 or RSI>60）")
            result["current_state"] = "戻り待ち"
            
            # 3. トリガー確認
            trigger_ok, trigger_desc = check_trigger(current, is_long=False)
            if trigger_ok:
                result["signal"] = SignalType.SHORT
                result["trigger"] = trigger_desc
                result["details"].append(f"✓ トリガー発生: {trigger_desc}")
                result["current_state"] = "🔴 売りシグナル点灯"
                result["risk_reward"] = calculate_risk_reward(df_main, is_long=False)
    else:
        result["details"].append("△ トレンド不明確（様子見）")
    
    return result
