"""
ポートフォリオ管理モジュール
ポジションサイズ計算、リスク管理
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Tuple
from database import (
    get_funds, update_funds, get_portfolio, get_holding,
    add_or_update_holding, update_stop_loss, sell_holding, delete_holding,
    add_transaction
)
from data_fetcher import get_ticker_info, get_current_price


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float
) -> int:
    """
    2%ルールに基づくポジションサイズ計算
    
    Args:
        account_balance: 総資産（現金 + 保有株評価額）
        risk_percent: リスク許容率（例: 0.02 = 2%）
        entry_price: エントリー価格
        stop_loss_price: 損切り価格
    
    Returns:
        推奨株数
    """
    if entry_price <= stop_loss_price:
        return 0
    
    risk_amount = account_balance * risk_percent
    risk_per_share = entry_price - stop_loss_price
    
    if risk_per_share <= 0:
        return 0
    
    position_size = int(risk_amount / risk_per_share)
    return max(0, position_size)


def calculate_max_shares(
    cash: float,
    price: float,
    unit: int = 1
) -> int:
    """
    最大購入可能株数を計算
    
    Args:
        cash: 利用可能現金
        price: 株価
        unit: 単元株数（日本株は100、米国株は1）
    
    Returns:
        購入可能株数
    """
    if price <= 0:
        return 0
    
    max_shares = int(cash / price)
    return (max_shares // unit) * unit


def calculate_total_risk_exposure(portfolio_data: List[Dict]) -> Tuple[float, float]:
    """
    ポートフォリオ全体のリスク額を計算
    
    Args:
        portfolio_data: ポートフォリオデータ（現在価格含む）
    
    Returns:
        (リスク額, リスク率)
    """
    total_risk = 0.0
    
    for holding in portfolio_data:
        if holding.get('stop_loss') and holding.get('current_price'):
            risk_per_share = holding['current_price'] - holding['stop_loss']
            if risk_per_share > 0:
                risk = risk_per_share * holding['quantity']
                total_risk += risk
    
    return total_risk


def get_portfolio_with_prices() -> List[Dict]:
    """
    ポートフォリオに現在価格と損益を追加して取得（キャッシュ利用）
    """
    portfolio = get_portfolio()
    
    for holding in portfolio:
        ticker = holding['ticker']
        
        # キャッシュ版を使用（APIコール削減）
        current_price = get_current_price(ticker)
        info = get_ticker_info(ticker)
        holding['name'] = info.get('name', ticker)
        
        if current_price:
            holding['current_price'] = current_price
            holding['market_value'] = current_price * holding['quantity']
            holding['cost_basis'] = holding['avg_cost'] * holding['quantity']
            holding['unrealized_pnl'] = holding['market_value'] - holding['cost_basis']
            holding['unrealized_pnl_pct'] = (
                (holding['unrealized_pnl'] / holding['cost_basis']) * 100
                if holding['cost_basis'] > 0 else 0
            )
            
            # 損切りまでの距離
            if holding.get('stop_loss'):
                holding['distance_to_sl'] = current_price - holding['stop_loss']
                holding['distance_to_sl_pct'] = (
                    (holding['distance_to_sl'] / current_price) * 100
                    if current_price > 0 else 0
                )
        else:
            holding['current_price'] = None
            holding['market_value'] = 0
            holding['unrealized_pnl'] = 0
    
    return portfolio


def calculate_total_assets(cash_jpy: float, cash_usd: float, portfolio: List[Dict]) -> Dict:
    """
    総資産を計算
    
    Returns:
        {
            'cash_jpy': 円現金,
            'cash_usd': ドル現金,
            'holdings_value_jpy': 円建て保有株評価額,
            'holdings_value_usd': ドル建て保有株評価額,
            'total_jpy': 円建て総資産,
            'total_usd': ドル建て総資産,
            'total_pnl': 含み損益合計
        }
    """
    holdings_jpy = 0.0
    holdings_usd = 0.0
    total_pnl = 0.0
    
    for h in portfolio:
        value = h.get('market_value', 0)
        pnl = h.get('unrealized_pnl', 0)
        
        if h.get('currency') == 'USD' or not h['ticker'].endswith('.T'):
            holdings_usd += value
        else:
            holdings_jpy += value
        
        total_pnl += pnl
    
    return {
        'cash_jpy': cash_jpy,
        'cash_usd': cash_usd,
        'holdings_value_jpy': holdings_jpy,
        'holdings_value_usd': holdings_usd,
        'total_jpy': cash_jpy + holdings_jpy,
        'total_usd': cash_usd + holdings_usd,
        'total_pnl': total_pnl
    }


# ============================================
# Streamlit UI コンポーネント
# ============================================

def render_asset_summary():
    """資産サマリーを表示"""
    funds = get_funds()
    portfolio = get_portfolio_with_prices()
    assets = calculate_total_assets(
        funds.get('JPY', 0),
        funds.get('USD', 0),
        portfolio
    )
    
    # 総リスク計算
    total_risk = calculate_total_risk_exposure(portfolio)
    total_assets = assets['total_jpy'] + (assets['total_usd'] * 150)  # 簡易換算
    risk_pct = (total_risk / total_assets * 100) if total_assets > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 総資産（円）",
            f"¥{assets['total_jpy']:,.0f}",
            help="現金 + 円建て保有株"
        )
    
    with col2:
        st.metric(
            "💵 現金余力（円）",
            f"¥{assets['cash_jpy']:,.0f}"
        )
    
    with col3:
        delta_color = "normal" if assets['total_pnl'] >= 0 else "inverse"
        st.metric(
            "📊 含み損益",
            f"¥{assets['total_pnl']:,.0f}",
            delta=f"{assets['total_pnl']:+,.0f}",
            delta_color=delta_color
        )
    
    with col4:
        if risk_pct > 10:
            st.error(f"⚠️ 総リスク率: {risk_pct:.1f}%")
        elif risk_pct > 5:
            st.warning(f"⚡ 総リスク率: {risk_pct:.1f}%")
        else:
            st.success(f"✅ 総リスク率: {risk_pct:.1f}%")
        st.caption(f"リスク額: ¥{total_risk:,.0f}")
    
    return assets, portfolio


def render_funds_input():
    """資金入力フォーム"""
    st.subheader("💰 資金管理")
    
    funds = get_funds()
    
    col1, col2 = st.columns(2)
    
    with col1:
        jpy = st.number_input(
            "円資金 (JPY)",
            min_value=0.0,
            value=float(funds.get('JPY', 0)),
            step=10000.0,
            format="%.0f"
        )
        if jpy != funds.get('JPY', 0):
            update_funds('JPY', jpy)
            st.rerun()
    
    with col2:
        usd = st.number_input(
            "ドル資金 (USD)",
            min_value=0.0,
            value=float(funds.get('USD', 0)),
            step=100.0,
            format="%.2f"
        )
        if usd != funds.get('USD', 0):
            update_funds('USD', usd)
            st.rerun()


def render_add_holding_form():
    """保有銘柄追加フォーム"""
    st.subheader("➕ 銘柄追加")
    
    with st.form("add_holding_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            ticker = st.text_input("銘柄コード", placeholder="AAPL or 7203.T")
            quantity = st.number_input("株数", min_value=1, value=100, step=1)
        
        with col2:
            avg_cost = st.number_input("平均取得単価", min_value=0.01, value=100.0, step=1.0)
            stop_loss = st.number_input("損切り価格 (任意)", min_value=0.0, value=0.0, step=1.0)
        
        submitted = st.form_submit_button("追加", use_container_width=True)
        
        if submitted and ticker:
            ticker = ticker.upper()
            currency = "USD" if not ticker.endswith('.T') else "JPY"
            sl = stop_loss if stop_loss > 0 else None
            
            add_or_update_holding(ticker, quantity, avg_cost, sl, currency)
            add_transaction(ticker, "BUY", quantity, avg_cost)
            st.success(f"{ticker} を追加しました")
            st.rerun()


def render_portfolio_table(portfolio: List[Dict]):
    """ポートフォリオテーブルを表示"""
    st.subheader("📦 保有銘柄一覧")
    
    if not portfolio:
        st.info("保有銘柄がありません")
        return
    
    for h in portfolio:
        stock_name = h.get('name', h['ticker'])
        with st.expander(f"**{h['ticker']}** - {stock_name} ({h['quantity']}株)", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("現在価格", f"{h.get('current_price', 'N/A'):.2f}" if h.get('current_price') else "取得中...")
                st.metric("平均取得単価", f"{h['avg_cost']:.2f}")
            
            with col2:
                pnl = h.get('unrealized_pnl', 0)
                pnl_pct = h.get('unrealized_pnl_pct', 0)
                st.metric(
                    "含み損益",
                    f"¥{pnl:,.0f}",
                    delta=f"{pnl_pct:+.2f}%"
                )
                st.metric("評価額", f"¥{h.get('market_value', 0):,.0f}")
            
            with col3:
                sl = h.get('stop_loss', 0)
                st.metric("損切り価格", f"{sl:.2f}" if sl else "未設定")
                
                if h.get('distance_to_sl_pct'):
                    dist = h['distance_to_sl_pct']
                    if dist < 3:
                        st.error(f"⚠️ SLまで {dist:.1f}%")
                    else:
                        st.info(f"SLまで {dist:.1f}%")
            
            # 損切り価格更新
            new_sl = st.number_input(
                "損切り価格を更新",
                min_value=0.0,
                value=float(sl) if sl else 0.0,
                step=1.0,
                key=f"sl_{h['ticker']}"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💾 SL更新", key=f"update_sl_{h['ticker']}"):
                    update_stop_loss(h['ticker'], new_sl)
                    st.success("更新しました")
                    st.rerun()
            
            with col_b:
                if st.button("🗑️ 削除", key=f"delete_{h['ticker']}"):
                    delete_holding(h['ticker'])
                    st.success("削除しました")
                    st.rerun()


def render_position_calculator(ticker: str, current_price: float, stop_loss_suggestion: float = None):
    """ポジションサイズ計算機"""
    st.subheader("🧮 購入シミュレーター")
    
    funds = get_funds()
    portfolio = get_portfolio_with_prices()
    assets = calculate_total_assets(funds.get('JPY', 0), funds.get('USD', 0), portfolio)
    
    # 通貨判定（かぶミニ対応: 日本株も1株単位）
    is_jpy = ticker.endswith('.T')
    cash = assets['cash_jpy'] if is_jpy else assets['cash_usd']
    total_assets = assets['total_jpy'] if is_jpy else assets['total_usd']
    unit = 1  # かぶミニ対応: 1株単位
    currency_symbol = "¥" if is_jpy else "$"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**銘柄**: {ticker}")
        st.markdown(f"**現在価格**: {currency_symbol}{current_price:,.2f}")
        st.markdown(f"**利用可能資金**: {currency_symbol}{cash:,.0f}")
    
    with col2:
        sl_price = st.number_input(
            "損切り予定価格",
            min_value=0.01,
            value=float(stop_loss_suggestion) if stop_loss_suggestion else current_price * 0.95,
            step=1.0
        )
        risk_pct = st.slider("リスク許容率 (%)", 1, 5, 2) / 100
    
    st.divider()
    
    # 計算結果（1株単位）
    max_shares = calculate_max_shares(cash, current_price, unit)
    recommended_shares = calculate_position_size(total_assets, risk_pct, current_price, sl_price)
    
    # かぶミニなので単元株調整は不要
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "🔥 最大購入可能（全力）",
            f"{max_shares:,}株",
            help="現金 ÷ 株価"
        )
        st.caption(f"必要資金: {currency_symbol}{max_shares * current_price:,.0f}")
    
    with col2:
        st.metric(
            "✅ 推奨ロット（2%ルール）",
            f"{recommended_shares:,}株",
            help="(総資産 × リスク率) ÷ (株価 - 損切り価格)"
        )
        st.caption(f"必要資金: {currency_symbol}{recommended_shares * current_price:,.0f}")
    
    # リスク表示
    risk_amount = recommended_shares * (current_price - sl_price)
    st.info(f"💡 推奨ロットでの最大損失: {currency_symbol}{risk_amount:,.0f} （総資産の{risk_pct*100:.0f}%）")
    
    return {
        'max_shares': max_shares,
        'recommended_shares': recommended_shares,
        'risk_amount': risk_amount
    }
