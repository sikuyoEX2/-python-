"""
売却判定アドバイザーモジュール (Sell Advisor)
保有株専用の売却タイミング判定システム

売却スコア:
- 80以上: 即時売却推奨
- 60-79: 利益確定推奨
- 59以下: ホールド継続
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from data_fetcher import fetch_stock_data, get_ticker_info
from indicators import calculate_ema, calculate_rsi


def calculate_sell_score(
    ticker: str,
    entry_price: float,
    stop_loss: float,
    quantity: int
) -> Dict:
    """
    売却スコアを算出（0-100点、高いほど売り推奨）
    
    Args:
        ticker: 銘柄コード
        entry_price: 取得単価
        stop_loss: 損切り価格
        quantity: 保有株数
    
    Returns:
        売却判定結果の辞書
    """
    result = {
        'ticker': ticker,
        'sell_score': 0,
        'reasons': [],
        'recommendation': 'ホールド',
        'urgency': '🟢 安全',
        'details': {}
    }
    
    try:
        # 株価データ取得
        df = fetch_stock_data(ticker, period="1mo", interval="1d")
        if df is None or len(df) < 20:
            result['reasons'].append("データ不足")
            return result
        
        # インジケーター計算
        df = calculate_ema(df, period=20)
        df = calculate_ema(df, period=200)
        df = calculate_rsi(df, period=14)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        current_price = latest['close']
        
        result['details']['current_price'] = current_price
        result['details']['rsi'] = latest['rsi']
        
        score = 0
        
        # ============================================
        # A. 損切り・トレンド崩壊判定 (Max 100点)
        # ============================================
        
        # 1. 損切りライン接触（即時売却）
        if stop_loss and current_price <= stop_loss:
            score = 100
            result['reasons'].append(f"⚠️ 損切りライン到達 (SL: ¥{stop_loss:,.0f})")
            result['recommendation'] = '【緊急】即時売却'
            result['urgency'] = '🔴 緊急'
            result['sell_score'] = score
            return result
        
        # 2. トレイリングストップ（最高値から5%下落）
        if len(df) >= 5:
            recent_high = df['high'].tail(20).max()
            drop_from_high = (recent_high - current_price) / recent_high * 100
            if drop_from_high >= 5 and current_price > entry_price:
                score += 40
                result['reasons'].append(f"📉 最高値から{drop_from_high:.1f}%下落（利益確保推奨）")
                result['details']['drop_from_high'] = drop_from_high
        
        # 3. トレンド転換 (Death Cross)
        if 'ema_20' in df.columns and 'ema_200' in df.columns:
            if 'ema_20' in latest.index:
                prev_ema20 = prev['ema_20'] if 'ema_20' in prev.index else latest['ema_20']
                ema_20_slope = latest['ema_20'] - prev_ema20
                if current_price < latest['ema_20'] and ema_20_slope < 0:
                    score += 30
                    result['reasons'].append("📊 トレンド転換シグナル（価格<20EMA、EMA下向き）")
        
        # ============================================
        # B. テクニカル過熱感・反転シグナル (Max 50点)
        # ============================================
        
        # 1. RSIピークアウト（70超えから下落）
        latest_rsi = latest.get('rsi') if hasattr(latest, 'get') else latest['rsi'] if 'rsi' in latest.index else None
        prev_rsi = prev.get('rsi') if hasattr(prev, 'get') else prev['rsi'] if 'rsi' in prev.index else None
        
        if latest_rsi is not None and prev_rsi is not None and not pd.isna(latest_rsi) and not pd.isna(prev_rsi):
            if prev_rsi > 70 and latest_rsi <= 70:
                score += 30
                result['reasons'].append(f"⚡ RSIピークアウト ({prev_rsi:.1f}→{latest_rsi:.1f})")
            elif latest_rsi > 80:
                score += 20
                result['reasons'].append(f"🔥 RSI過熱 ({latest_rsi:.1f})")
        
        # 2. 反転ローソク足パターン
        body = abs(latest['close'] - latest['open'])
        upper_wick = latest['high'] - max(latest['open'], latest['close'])
        lower_wick = min(latest['open'], latest['close']) - latest['low']
        total_range = latest['high'] - latest['low']
        
        if total_range > 0:
            # 長い上ヒゲ（高値圏での売り圧力）
            if upper_wick > body * 2 and current_price > entry_price * 1.05:
                score += 20
                result['reasons'].append("🕯️ 長い上ヒゲ出現（売り圧力）")
            
            # 陰線の包み足
            if len(df) > 1:
                prev_body = prev['close'] - prev['open']
                curr_body = latest['close'] - latest['open']
                if prev_body > 0 and curr_body < 0:
                    if abs(curr_body) > abs(prev_body):
                        score += 15
                        result['reasons'].append("🕯️ 陰線包み足（反転シグナル）")
        
        # ============================================
        # C. 含み損益に基づく調整
        # ============================================
        
        pnl_pct = (current_price - entry_price) / entry_price * 100
        result['details']['pnl_pct'] = pnl_pct
        
        # 含み損が拡大中の場合、スコアを上げる
        if pnl_pct <= -2:
            score += 15
            result['reasons'].append(f"📉 含み損 {pnl_pct:.1f}%（2%ルール警告）")
        
        # ============================================
        # 最終スコア計算
        # ============================================
        
        result['sell_score'] = min(score, 100)
        
        # 推奨判定
        if result['sell_score'] >= 80:
            result['recommendation'] = '即時売却'
            result['urgency'] = '🔴 危険'
        elif result['sell_score'] >= 60:
            result['recommendation'] = '利益確定推奨'
            result['urgency'] = '🟡 注意'
        else:
            result['recommendation'] = 'ホールド'
            result['urgency'] = '🟢 安全'
        
        if not result['reasons']:
            result['reasons'].append("✅ 特に問題なし")
        
    except Exception as e:
        result['reasons'].append(f"分析エラー: {str(e)}")
    
    return result


def analyze_portfolio_sell_signals(portfolio: List[Dict]) -> List[Dict]:
    """
    ポートフォリオ全体の売却判定を実行
    
    Args:
        portfolio: 保有銘柄リスト
    
    Returns:
        売却判定結果リスト
    """
    results = []
    
    for holding in portfolio:
        ticker = holding['ticker']
        entry_price = holding.get('avg_cost', 0)
        stop_loss = holding.get('stop_loss', 0)
        quantity = holding.get('quantity', 0)
        
        if entry_price <= 0:
            continue
        
        sell_result = calculate_sell_score(
            ticker=ticker,
            entry_price=entry_price,
            stop_loss=stop_loss,
            quantity=quantity
        )
        
        # 保有情報を追加
        sell_result['name'] = holding.get('name', ticker)
        sell_result['quantity'] = quantity
        sell_result['entry_price'] = entry_price
        sell_result['stop_loss'] = stop_loss
        
        results.append(sell_result)
    
    # 売却スコア順にソート（危険度高い順）
    results = sorted(results, key=lambda x: x['sell_score'], reverse=True)
    
    return results


def render_sell_advisor_section(portfolio: List[Dict]):
    """
    売却アドバイザーセクションを表示
    
    Args:
        portfolio: 保有銘柄リスト
    """
    st.subheader("🔔 売却判定アドバイザー")
    
    if not portfolio:
        st.info("保有銘柄がありません")
        return
    
    # 売却判定ボタン
    if st.button("📊 売却判定を実行", use_container_width=True):
        with st.spinner("保有銘柄を分析中..."):
            results = analyze_portfolio_sell_signals(portfolio)
            st.session_state.sell_advisor_results = results
    
    # 結果表示
    if 'sell_advisor_results' in st.session_state:
        results = st.session_state.sell_advisor_results
        
        # 緊急アラート（スコア80以上）
        urgent = [r for r in results if r['sell_score'] >= 80]
        if urgent:
            st.error("⚠️ **緊急売却推奨銘柄があります！**")
            for r in urgent:
                st.error(f"🔴 **{r['ticker']}** ({r['name']}) - スコア: {r['sell_score']}点")
                for reason in r['reasons']:
                    st.write(f"   {reason}")
        
        # 結果テーブル
        st.markdown("### 📋 保有銘柄 売却判定一覧")
        
        for r in results:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1.5])
            
            with col1:
                st.write(f"**{r['ticker']}** - {r['name']}")
                st.caption(f"{r['quantity']}株 / 取得: ¥{r['entry_price']:,.0f}")
            
            with col2:
                current = r['details'].get('current_price', 0)
                pnl = r['details'].get('pnl_pct', 0)
                st.metric("現在値", f"¥{current:,.0f}", delta=f"{pnl:+.1f}%")
            
            with col3:
                score = r['sell_score']
                st.metric("売却スコア", f"{score}点")
                st.caption(r['urgency'])
            
            with col4:
                st.info(f"**{r['recommendation']}**")
                with st.expander("詳細", expanded=False):
                    for reason in r['reasons']:
                        st.write(reason)
            
            st.divider()


def get_urgent_sell_alerts(portfolio: List[Dict]) -> List[Dict]:
    """
    緊急売却アラートを取得（スコア80以上）
    
    Args:
        portfolio: 保有銘柄リスト
    
    Returns:
        緊急アラートリスト
    """
    if not portfolio:
        return []
    
    results = analyze_portfolio_sell_signals(portfolio)
    return [r for r in results if r['sell_score'] >= 80]
