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

# 定期タスクチェック（エラー時は続行）
try:
    from scheduled_tasks import check_and_run_scheduled_tasks
    scheduled_results = check_and_run_scheduled_tasks()
    if scheduled_results.get('morning_ran') or scheduled_results.get('afternoon_ran'):
        print(f"Scheduled scan executed at {datetime.now()}")
except Exception as e:
    print(f"Scheduled task skipped: {e}")

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
    
    # === 取引時間チェック ===
    now = datetime.now()
    is_japanese_stock = ticker.endswith('.T')
    
    if is_japanese_stock:
        # 日本株: 9:00-15:30 のみ通知
        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if not (market_open <= now <= market_close):
            return  # 取引時間外は通知しない
        # 土日チェック（0=月曜, 6=日曜）
        if now.weekday() >= 5:
            return  # 土日は通知しない
    else:
        # 米国株: 日本時間 23:30-6:00 (サマータイム: 22:30-5:00)
        # 簡易チェック: 営業日のみ
        if now.weekday() >= 5:
            return  # 土日は通知しない
    
    # 最後の通知時刻をチェック（クールダウン: 30分）
    if 'last_notification_time' not in st.session_state:
        st.session_state.last_notification_time = {}
    
    last_signal = st.session_state.last_signals.get(ticker)
    last_notify_time = st.session_state.last_notification_time.get(ticker)
    
    # 30分以内に同じ銘柄で通知していたらスキップ
    cooldown_minutes = 30
    if last_notify_time:
        elapsed = (datetime.now() - last_notify_time).total_seconds() / 60
        if elapsed < cooldown_minutes and signal_type == last_signal:
            return  # クールダウン中は通知しない
    
    if signal_type != SignalType.NONE and signal_type != last_signal:
        st.session_state.last_signals[ticker] = signal_type
        st.session_state.last_notification_time[ticker] = datetime.now()
        
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
    
    current_price = df_main.iloc[-1]['close']
    prev_price = df_main.iloc[-2]['close']
    change_pct = ((current_price - prev_price) / prev_price * 100)
    rsi_value = df_main.iloc[-1]['rsi']
    
    # テクニカルスコア計算
    tech_score = 0
    # トレンド（40点）
    if df_main.iloc[-1]['close'] > df_main.iloc[-1].get('ema_200', 0):
        tech_score += 20
    if df_main.iloc[-1].get('ema_20', 0) > df_main.iloc[-1].get('ema_200', 0):
        tech_score += 20
    # モメンタム（40点）
    if 30 <= rsi_value <= 40:
        tech_score += 30
    elif rsi_value < 30:
        tech_score += 25
    elif 40 < rsi_value <= 60:
        tech_score += 20
    # 出来高（10点デフォルト）
    tech_score += 10
    # 価格ボーナス
    price_bonus = 10 if current_price < 1000 else (5 if current_price < 3000 else 0)
    base_score = tech_score + price_bonus
    # ランク判定
    if base_score >= 80:
        rank = "S"
    elif base_score >= 60:
        rank = "A"
    elif base_score >= 40:
        rank = "B"
    else:
        rank = "C"
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("現在価格", f"{current_price:.2f}", delta=f"{change_pct:.2f}%")
    
    with col2:
        trend_color = "🟢" if "上昇" in signal_result['trend'] else "🔴" if "下落" in signal_result['trend'] else "⚪"
        st.metric("トレンド", trend_color)
        st.caption(signal_result['trend'])
    
    with col3:
        st.metric("RSI (14)", f"{rsi_value:.1f}")
    
    with col4:
        # スコアとランク表示
        rank_colors = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉"}
        st.metric(f"{rank_colors.get(rank, '')} ランク", rank)
        st.caption(f"スコア: {base_score}点")
    
    with col5:
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
    
    # AI感情分析（オプション）
    st.divider()
    with st.expander("🤖 AI感情分析（Gemini）", expanded=False):
        if st.button("📊 ニュース感情を分析", key=f"ai_analyze_{ticker}"):
            try:
                from sentiment import render_sentiment_panel
                render_sentiment_panel(ticker)
            except ImportError:
                st.error("AI機能のライブラリがインストールされていません")
            except Exception as e:
                st.error(f"AI分析エラー: {e}")
    
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
    tab1, tab2, tab3, tab4 = st.tabs(["📦 保有銘柄", "🔔 売却判定", "➕ 銘柄追加", "💰 資金管理"])
    
    with tab1:
        render_portfolio_table(portfolio)
    
    with tab2:
        # 売却判定アドバイザー
        try:
            from sell_advisor import render_sell_advisor_section
            render_sell_advisor_section(portfolio)
        except ImportError as e:
            st.error(f"売却判定モジュールを読み込めませんでした: {e}")
    
    with tab3:
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
    
    with tab4:
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
    
    # === 含み損アラート表示 ===
    loss_alerts = st.session_state.get('loss_alerts', [])
    if loss_alerts:
        with st.expander("⚠️ 含み損アラート（-2%以上）", expanded=True):
            for alert in loss_alerts:
                st.error(f"🔴 **{alert['ticker']}** ({alert['name']}) : {alert['pnl_pct']:.1f}%")
    
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
                from database import add_to_watchlist
                add_to_watchlist(ticker_input.upper())
                st.success(f"{ticker_input.upper()} を追加")
                st.rerun()
        
        for i, ticker in enumerate(st.session_state.watchlist):
            col1, col2 = st.columns([3, 1])
            with col1:
                # 銘柄名を取得して表示
                try:
                    info = get_ticker_info(ticker)
                    display_name = info.get('name', ticker)[:15]
                except:
                    display_name = ticker
                if st.button(f"{ticker}: {display_name}", key=f"watch_{i}", use_container_width=True):
                    st.session_state.selected_ticker = ticker
            with col2:
                if st.button("×", key=f"remove_{i}"):
                    from database import remove_from_watchlist
                    remove_from_watchlist(ticker)
                    st.rerun()
        
        if st.session_state.watchlist:
            # AI分析トグル
            use_ai_batch = st.toggle("🤖 AI分析を使用", value=False, help="一括分析時にGemini AIでニュース感情も分析")
            st.session_state.use_ai_batch = use_ai_batch
            
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
        
        use_ai = st.session_state.get('use_ai_batch', False)
        if use_ai:
            st.info("🤖 AI分析モードON（Gemini API使用）")
        
        tabs = st.tabs(st.session_state.watchlist)
        for tab, ticker in zip(tabs, st.session_state.watchlist):
            with tab:
                with st.spinner(f"{ticker} を分析中..."):
                    result = analyze_ticker(ticker)
                    render_analysis_result(ticker, result)
                    
                    # AI分析（トグルON時のみ）
                    if use_ai:
                        try:
                            from sentiment import render_sentiment_panel
                            st.divider()
                            st.markdown("### 🤖 AI感情分析")
                            render_sentiment_panel(ticker)
                        except ImportError:
                            st.warning("AI機能のライブラリがインストールされていません")
                        except Exception as e:
                            st.error(f"AI分析エラー: {e}")
    
    elif analyze_button or st.session_state.get('selected_ticker'):
        selected = st.session_state.get('selected_ticker')
        ticker = (selected if selected else ticker_input) or "AAPL"
        ticker = ticker.upper()
        st.session_state.selected_ticker = None
        
        with st.spinner(f"{ticker} のデータを取得中..."):
            result = analyze_ticker(ticker)
            render_analysis_result(ticker, result)
    
    else:
        # 保有銘柄一覧を表示
        st.subheader("📦 保有銘柄一覧")
        if portfolio:
            for h in portfolio:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    name = h.get('name', h['ticker'])
                    st.write(f"**{h['ticker']}** - {name}")
                with col2:
                    st.metric("現在価格", f"¥{h.get('current_price') or 0:,.0f}")
                with col3:
                    pnl = h.get('unrealized_pnl') or 0
                    pnl_pct = h.get('unrealized_pnl_pct') or 0
                    color = "normal" if pnl >= 0 else "inverse"
                    st.metric("含み損益", f"¥{pnl:,.0f}", delta=f"{pnl_pct:+.1f}%", delta_color=color)
                with col4:
                    if st.button("📊 分析", key=f"home_analyze_{h['ticker']}"):
                        st.session_state.selected_ticker = h['ticker']
                        st.rerun()
                st.divider()
        else:
            st.info("保有銘柄がありません。「💼 ポートフォリオ」ページで銘柄を追加してください。")


if __name__ == "__main__":
    main()
