"""
株価監視・資金管理Webアプリ
Streamlit メインアプリケーション（改訂版）
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# ローカルモジュール
from data_fetcher import fetch_multi_timeframe_data, get_ticker_info
from indicators import add_indicators
from patterns import detect_patterns
from signals import generate_signal, SignalType
from chart import create_candlestick_chart
from notifications import (
    NotificationManager, 
    render_notification_settings, 
    get_webhook_notifier,
    get_browser_notification_script
)
from glossary import render_glossary_page
from screener import render_screener_page
from portfolio_manager import (
    render_asset_summary,
    render_funds_input,
    render_add_holding_form,
    render_portfolio_table,
    render_position_calculator,
    get_portfolio_with_prices,
    calculate_position_size
)
from database import get_funds, init_database, sync_to_localstorage, render_data_loader

# データベース初期化（エラー時は続行）
try:
    init_database()
except Exception as e:
    print(f"Database init skipped: {e}")

# ページ設定
st.set_page_config(
    page_title="株価シグナル監視",
    page_icon="📈",
    layout="wide"
)

# localStorageからデータを読み込むUI
render_data_loader()

# セッション状態の初期化
if 'notification_manager' not in st.session_state:
    st.session_state.notification_manager = NotificationManager()
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []
if 'last_signals' not in st.session_state:
    st.session_state.last_signals = {}


def analyze_ticker(ticker: str) -> dict:
    """銘柄を分析してシグナル情報を返す"""
    try:
        df_main, df_higher = fetch_multi_timeframe_data(ticker)
        info = get_ticker_info(ticker)
        df_main = add_indicators(df_main)
        df_higher = add_indicators(df_higher)
        df_main = detect_patterns(df_main)
        signal_result = generate_signal(df_main, df_higher)
        
        return {
            "success": True,
            "df_main": df_main,
            "df_higher": df_higher,
            "info": info,
            "signal": signal_result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_and_notify(ticker: str, signal_result: dict):
    """シグナルをチェックして通知を送信"""
    signal_type = signal_result['signal']
    last_signal = st.session_state.last_signals.get(ticker)
    
    if signal_type != SignalType.NONE and signal_type != last_signal:
        st.session_state.last_signals[ticker] = signal_type
        
        notify_type = "buy" if signal_type == SignalType.LONG else "sell"
        st.session_state.notification_manager.add_alert(
            ticker, notify_type, signal_result['current_state']
        )
        
        notifier = get_webhook_notifier()
        rr = signal_result.get('risk_reward', {})
        notifier.send_all(
            ticker=ticker,
            signal_type=notify_type,
            message=f"{signal_result['current_state']} - トリガー: {signal_result['trigger']}",
            entry=rr.get('entry'),
            stop_loss=rr.get('stop_loss'),
            take_profit=rr.get('take_profit')
        )
        
        script = get_browser_notification_script(ticker, notify_type, signal_result['current_state'])
        components.html(script, height=0)
        
        return True
    return False


def render_analysis_result(ticker: str, result: dict):
    """分析結果を表示"""
    if not result['success']:
        st.error(f"エラーが発生しました: {result['error']}")
        st.info("銘柄コードを確認してください（例: AAPL, NVDA, 7203.T, 9984.T）")
        return
    
    df_main = result['df_main']
    info = result['info']
    signal_result = result['signal']
    
    is_new_signal = check_and_notify(ticker, signal_result)
    
    # ステータスパネル
    st.subheader(f"📊 {info['name']} ({ticker})")
    
    col1, col2, col3, col4 = st.columns(4)
    
    current_price = df_main.iloc[-1]['close']
    prev_price = df_main.iloc[-2]['close']
    change_pct = ((current_price - prev_price) / prev_price * 100)
    
    with col1:
        st.metric("現在価格", f"{current_price:.2f}", delta=f"{change_pct:.2f}%")
    
    with col2:
        trend_color = "🟢" if "上昇" in signal_result['trend'] else "🔴" if "下落" in signal_result['trend'] else "⚪"
        st.metric("トレンド", trend_color)
        st.caption(signal_result['trend'])
    
    with col3:
        rsi_value = df_main.iloc[-1]['rsi']
        st.metric("RSI (14)", f"{rsi_value:.1f}")
    
    with col4:
        if signal_result['signal'] == SignalType.LONG:
            st.success(f"**{signal_result['current_state']}**")
        elif signal_result['signal'] == SignalType.SHORT:
            st.error(f"**{signal_result['current_state']}**")
        else:
            st.info(f"**{signal_result['current_state']}**")
    
    # シグナルアラート
    if is_new_signal:
        if signal_result['signal'] == SignalType.LONG:
            st.success(f"🟢 **買いシグナル検出！** トリガー: {signal_result['trigger']}")
            st.balloons()
        else:
            st.error(f"🔴 **売りシグナル検出！** トリガー: {signal_result['trigger']}")
    
    # 判定詳細
    with st.expander("📋 判定詳細", expanded=True):
        for detail in signal_result['details']:
            st.write(detail)
    
    # 購入シミュレーター（常に表示）
    st.divider()
    rr = signal_result.get('risk_reward', {})
    stop_loss_suggestion = rr.get('stop_loss') if rr else current_price * 0.95
    render_position_calculator(ticker, current_price, stop_loss_suggestion)
    
    # リスクリワード表示（シグナル時のみ）
    if rr:
            st.subheader("💰 リスクリワード")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("エントリー価格", f"{rr['entry']:.2f}")
            with col2:
                st.metric("損切り目安", f"{rr['stop_loss']:.2f}", delta=f"-{rr['risk']:.2f}")
            with col3:
                st.metric("利確目標 (RR 1:2)", f"{rr['take_profit']:.2f}", delta=f"+{rr['reward']:.2f}")
    
    # チャート表示
    st.subheader("📈 チャート")
    fig = create_candlestick_chart(df_main, ticker)
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def render_portfolio_page():
    """ポートフォリオ管理ページ"""
    st.title("💼 ポートフォリオ管理")
    
    # 資産サマリー
    assets, portfolio = render_asset_summary()
    
    st.divider()
    
    # タブ
    tab1, tab2, tab3 = st.tabs(["📦 保有銘柄", "➕ 銘柄追加", "💰 資金管理"])
    
    with tab1:
        render_portfolio_table(portfolio)
    
    with tab2:
        render_add_holding_form()
        
        st.divider()
        
        # 任意の銘柄で購入シミュレーション
        st.subheader("🧮 任意銘柄の購入シミュレーション")
        ticker_sim = st.text_input("銘柄コード", placeholder="AAPL or 7203.T", key="sim_ticker")
        
        if ticker_sim:
            ticker_sim = ticker_sim.upper()
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker_sim)
                price = stock.info.get('regularMarketPrice') or stock.info.get('currentPrice')
                if price:
                    render_position_calculator(ticker_sim, price)
                else:
                    st.warning("価格を取得できませんでした")
            except Exception as e:
                st.error(f"エラー: {e}")
    
    with tab3:
        render_funds_input()


def main():
    """メイン関数"""
    
    # サイドバー - ナビゲーション
    with st.sidebar:
        st.header("📍 ナビゲーション")
        page = st.radio(
            "ページを選択",
            ["📈 シグナル監視", "🔍 スクリーナー", "💼 ポートフォリオ", "📚 用語解説"],
            label_visibility="collapsed"
        )
        st.divider()
    
    # スクリーナーから詳細分析への遷移（フラグは即座にクリア）
    from_screener = st.session_state.pop('go_to_signal', False)
    if from_screener:
        page = "📈 シグナル監視"
    
    # ページ分岐
    if page == "📚 用語解説":
        render_glossary_page()
        return
    
    if page == "🔍 スクリーナー":
        render_screener_page()
        return
    
    if page == "💼 ポートフォリオ":
        render_portfolio_page()
        return
    
    # ===== シグナル監視ページ =====
    
    # 資産サマリー（上部に常時表示）
    assets, portfolio = render_asset_summary()
    
    st.divider()
    
    st.title("📈 株価監視・売買シグナル通知")
    
    # サイドバー（続き）
    with st.sidebar:
        st.header("⚙️ 設定")
        
        ticker_input = st.text_input(
            "銘柄コード",
            value="",
            placeholder="AAPL, 7203.T など",
            help="例: AAPL（米国株）, 7203.T（日本株）"
        )
        
        analyze_button = st.button("🔍 分析開始", type="primary", use_container_width=True)
        
        st.divider()
        
        # ウォッチリスト
        st.subheader("📋 ウォッチリスト")
        
        if st.button("➕ リストに追加", use_container_width=True):
            if ticker_input and ticker_input.upper() not in st.session_state.watchlist:
                st.session_state.watchlist.append(ticker_input.upper())
                st.success(f"{ticker_input.upper()} を追加")
        
        for i, ticker in enumerate(st.session_state.watchlist):
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(ticker, key=f"watch_{i}", use_container_width=True):
                    st.session_state.selected_ticker = ticker
            with col2:
                if st.button("×", key=f"remove_{i}"):
                    st.session_state.watchlist.remove(ticker)
                    st.rerun()
        
        if st.session_state.watchlist:
            if st.button("🔄 全銘柄を一括分析", use_container_width=True):
                st.session_state.batch_analyze = True
        
        st.divider()
        
        # 通知設定
        render_notification_settings()
        
        st.divider()
        
        # 通知履歴
        st.subheader("📜 通知履歴")
        history = st.session_state.notification_manager.get_history(5)
        if history:
            for alert in history:
                icon = "🟢" if alert['type'] == 'buy' else "🔴" if alert['type'] == 'sell' else "ℹ️"
                time_str = alert['timestamp'].strftime("%H:%M")
                st.caption(f"{time_str} {icon} {alert['ticker']}")
        else:
            st.caption("履歴なし")
    
    # メインコンテンツ
    if st.session_state.get('batch_analyze'):
        st.session_state.batch_analyze = False
        st.subheader("📊 一括分析結果")
        
        tabs = st.tabs(st.session_state.watchlist)
        for tab, ticker in zip(tabs, st.session_state.watchlist):
            with tab:
                with st.spinner(f"{ticker} を分析中..."):
                    result = analyze_ticker(ticker)
                    render_analysis_result(ticker, result)
    
    elif analyze_button or st.session_state.get('selected_ticker'):
        selected = st.session_state.get('selected_ticker')
        ticker = (selected if selected else ticker_input) or "AAPL"
        ticker = ticker.upper()
        st.session_state.selected_ticker = None
        
        with st.spinner(f"{ticker} のデータを取得中..."):
            result = analyze_ticker(ticker)
            render_analysis_result(ticker, result)
    
    else:
        st.info("👈 サイドバーで銘柄コードを入力し、「分析開始」をクリックしてください")
        
        st.markdown("""
        ### 使い方
        1. **銘柄コード入力**: 米国株は `AAPL`, `NVDA` など、日本株は `7203.T` など
        2. **分析開始**: シグナル確認 + 購入可能株数を計算
        3. **ポートフォリオ**: 保有銘柄・資金を管理
        
        ### 新機能
        - 💼 **ポートフォリオ管理**: 保有銘柄と資金を登録
        - 🧮 **購入シミュレーター**: 2%ルールで推奨株数を計算
        - ⚠️ **総リスクモニター**: 全銘柄が損切りになった場合の最大損失を表示
        """)
    
    # 下部: ポートフォリオプレビュー
    st.divider()
    with st.expander("📦 保有銘柄（プレビュー）", expanded=False):
        if portfolio:
            df = pd.DataFrame(portfolio)
            df_display = df[['ticker', 'quantity', 'avg_cost', 'current_price', 'unrealized_pnl', 'stop_loss']].copy()
            df_display.columns = ['銘柄', '株数', '取得単価', '現在価格', '含み損益', '損切り']
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("保有銘柄なし → 「💼 ポートフォリオ」ページで追加")


if __name__ == "__main__":
    main()
