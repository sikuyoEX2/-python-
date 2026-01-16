"""
定期通知スケジューラーモジュール
朝8:00と15:15に自動的にスキャンと通知を実行
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time


def should_run_morning_scan() -> bool:
    """朝8:00のスキャンを実行すべきかチェック"""
    now = datetime.now()
    
    # 土日は実行しない
    if now.weekday() >= 5:
        return False
    
    # 8:00-8:05の間のみ実行
    if not (now.hour == 8 and now.minute < 5):
        return False
    
    # 今日既に実行済みかチェック
    last_run = st.session_state.get('last_morning_scan')
    if last_run and last_run.date() == now.date():
        return False
    
    return True


def should_run_afternoon_scan() -> bool:
    """15:15のスキャンを実行すべきかチェック"""
    now = datetime.now()
    
    # 土日は実行しない
    if now.weekday() >= 5:
        return False
    
    # 15:15-15:20の間のみ実行
    if not (now.hour == 15 and 15 <= now.minute < 20):
        return False
    
    # 今日既に実行済みかチェック
    last_run = st.session_state.get('last_afternoon_scan')
    if last_run and last_run.date() == now.date():
        return False
    
    return True


def run_scheduled_portfolio_scan():
    """
    保有銘柄のシグナルをスキャンして通知
    """
    from sell_advisor import analyze_portfolio_sell_signals
    from portfolio_manager import get_portfolio_with_prices
    from signals import generate_signal, SignalType
    from data_fetcher import fetch_stock_data
    from indicators import add_indicators
    from notifications import get_webhook_notifier
    
    portfolio = get_portfolio_with_prices()
    alerts = []
    
    for holding in portfolio:
        ticker = holding['ticker']
        try:
            df = fetch_stock_data(ticker, period="5d", interval="15m")
            if df is not None and len(df) > 0:
                df = add_indicators(df)
                signal_result = generate_signal(df, df)  # 簡易版
                
                if signal_result['signal'] != SignalType.NONE:
                    alerts.append({
                        'ticker': ticker,
                        'name': holding.get('name', ticker),
                        'signal': signal_result['signal'],
                        'trigger': signal_result.get('trigger', '')
                    })
        except:
            continue
    
    # 通知送信
    if alerts:
        notifier = get_webhook_notifier()
        message_lines = ["📊 **保有銘柄シグナル**\n"]
        for a in alerts:
            icon = "🟢" if "買い" in a['signal'] else "🔴"
            message_lines.append(f"{icon} {a['ticker']} ({a['name']}): {a['signal']}")
        
        notifier.send_all(
            ticker="PORTFOLIO",
            signal_type="info",
            message="\n".join(message_lines)
        )
    
    return alerts


def run_scheduled_screener_scan(use_ai: bool = False) -> List[Dict]:
    """
    楽天証券かぶミニ銘柄をスキャンしてトップ3を通知
    """
    from screener import screen_stocks, RAKUTEN_MINI_STOCKS
    from notifications import get_webhook_notifier
    
    # クイックモード（100銘柄）でスキャン
    quick_list = RAKUTEN_MINI_STOCKS[:100]
    
    results = screen_stocks(
        stock_list=quick_list,
        max_price=10000,
        use_parallel=True,
        max_workers=10
    )
    
    if not results:
        return []
    
    # 買いシグナル銘柄のみ抽出
    buy_signals = [r for r in results if r.get('signal') == '買い']
    
    # スコア順にソート
    buy_signals = sorted(buy_signals, key=lambda x: x.get('base_score', 0), reverse=True)
    
    # トップ3を取得
    top3 = buy_signals[:3]
    
    # AI分析（オプション）
    if use_ai and top3:
        try:
            from sentiment import NewsAnalyzer
            analyzer = NewsAnalyzer()
            
            for stock in top3:
                ticker = stock['ticker']
                news = analyzer.get_news(ticker)
                if news:
                    score, reason = analyzer.analyze_news(ticker, news[0].get('title', ''))
                    stock['ai_score'] = score
                    stock['ai_reason'] = reason
                    # 統合スコア計算
                    tech_score = stock.get('tech_score', 50)
                    stock['total_score'] = (tech_score * 0.7) + (score * 0.3) + stock.get('price_bonus', 0)
                time.sleep(4)  # API制限対策
        except:
            pass
        
        # 統合スコアで再ソート
        top3 = sorted(top3, key=lambda x: x.get('total_score', x.get('base_score', 0)), reverse=True)
    
    # 通知送信
    if top3:
        notifier = get_webhook_notifier()
        message_lines = ["🔍 **本日のおすすめ銘柄 TOP3**\n"]
        
        for i, stock in enumerate(top3, 1):
            score = stock.get('total_score', stock.get('base_score', 0))
            rank = stock.get('rank', 'C')
            message_lines.append(
                f"{i}. [{rank}] {stock['ticker']} ({stock['name']})\n"
                f"   ¥{stock['price']:,.0f} / RSI: {stock.get('rsi', 0):.1f} / スコア: {score:.1f}"
            )
        
        notifier.send_all(
            ticker="SCREENER",
            signal_type="info",
            message="\n".join(message_lines)
        )
    
    return top3


def check_and_run_scheduled_tasks():
    """
    定期タスクをチェックして実行
    ※この関数はアプリ起動時に呼び出される
    """
    results = {
        'morning_ran': False,
        'afternoon_ran': False,
        'portfolio_alerts': [],
        'top3_stocks': []
    }
    
    # 朝8:00のスキャン
    if should_run_morning_scan():
        st.session_state.last_morning_scan = datetime.now()
        results['morning_ran'] = True
        results['portfolio_alerts'] = run_scheduled_portfolio_scan()
        results['top3_stocks'] = run_scheduled_screener_scan(use_ai=True)
    
    # 15:15のスキャン
    if should_run_afternoon_scan():
        st.session_state.last_afternoon_scan = datetime.now()
        results['afternoon_ran'] = True
        results['portfolio_alerts'] = run_scheduled_portfolio_scan()
        results['top3_stocks'] = run_scheduled_screener_scan(use_ai=True)
    
    return results


def render_scheduled_task_status():
    """定期タスクのステータスを表示"""
    now = datetime.now()
    
    st.subheader("⏰ 定期スキャン")
    
    col1, col2 = st.columns(2)
    
    with col1:
        last_morning = st.session_state.get('last_morning_scan')
        if last_morning:
            st.success(f"朝スキャン: {last_morning.strftime('%m/%d %H:%M')}")
        else:
            st.info("朝スキャン: 未実行")
        st.caption("毎日 8:00 に実行")
    
    with col2:
        last_afternoon = st.session_state.get('last_afternoon_scan')
        if last_afternoon:
            st.success(f"午後スキャン: {last_afternoon.strftime('%m/%d %H:%M')}")
        else:
            st.info("午後スキャン: 未実行")
        st.caption("毎日 15:15 に実行")
    
    # 手動実行ボタン
    if st.button("🔄 今すぐスキャン実行", use_container_width=True):
        with st.spinner("スキャン中..."):
            portfolio_alerts = run_scheduled_portfolio_scan()
            top3 = run_scheduled_screener_scan(use_ai=False)  # 手動時はAIなし（高速化）
            
            st.success("スキャン完了！")
            if portfolio_alerts:
                st.write("**保有銘柄シグナル:**")
                for a in portfolio_alerts:
                    st.write(f"- {a['ticker']}: {a['signal']}")
            if top3:
                st.write("**おすすめTOP3:**")
                for i, s in enumerate(top3, 1):
                    st.write(f"{i}. {s['ticker']} ({s['name']}) - スコア: {s.get('base_score', 0)}")
