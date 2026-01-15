"""
データベースモジュール（Cookie永続化版）
extra-streamlit-componentsのCookieManagerを使用
"""
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional
import json

# CookieManager初期化
def get_cookie_manager():
    """CookieManagerを取得"""
    try:
        import extra_streamlit_components as stx
        return stx.CookieManager()
    except ImportError:
        return None


def init_database():
    """データベースを初期化（session_state + Cookie）"""
    if 'db_initialized' not in st.session_state:
        st.session_state.db_initialized = False
    
    if 'funds' not in st.session_state:
        st.session_state.funds = {'JPY': 0.0, 'USD': 0.0}
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []
    if 'transactions' not in st.session_state:
        st.session_state.transactions = []
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []
    
    # Cookieからデータを読み込み（初回のみ）
    if not st.session_state.db_initialized:
        load_from_cookies()
        st.session_state.db_initialized = True


def load_from_cookies():
    """Cookieからデータを読み込み"""
    cookie_manager = get_cookie_manager()
    if cookie_manager is None:
        return
    
    try:
        # 資金データ
        funds_json = cookie_manager.get('stock_app_funds')
        if funds_json:
            st.session_state.funds = json.loads(funds_json)
        
        # ポートフォリオ
        portfolio_json = cookie_manager.get('stock_app_portfolio')
        if portfolio_json:
            st.session_state.portfolio = json.loads(portfolio_json)
        
        # ウォッチリスト
        watchlist_json = cookie_manager.get('stock_app_watchlist')
        if watchlist_json:
            st.session_state.watchlist = json.loads(watchlist_json)
    except Exception as e:
        print(f"Cookie load error: {e}")


def save_to_cookies():
    """現在のデータをCookieに保存"""
    cookie_manager = get_cookie_manager()
    if cookie_manager is None:
        return
    
    try:
        cookie_manager.set('stock_app_funds', json.dumps(st.session_state.funds), max_age=60*60*24*365)
        cookie_manager.set('stock_app_portfolio', json.dumps(st.session_state.portfolio), max_age=60*60*24*365)
        cookie_manager.set('stock_app_watchlist', json.dumps(st.session_state.get('watchlist', [])), max_age=60*60*24*365)
    except Exception as e:
        print(f"Cookie save error: {e}")


def sync_to_localstorage():
    """Cookieに保存（後方互換性のため残す）"""
    save_to_cookies()


def render_data_loader():
    """データ読み込み（後方互換性のため残す）"""
    pass


# ============================================
# 資金管理
# ============================================

def get_funds() -> Dict[str, float]:
    """資金を取得"""
    init_database()
    return st.session_state.funds.copy()


def update_funds(currency: str, amount: float):
    """資金を更新"""
    init_database()
    st.session_state.funds[currency] = amount
    save_to_cookies()


# ============================================
# ポートフォリオ管理
# ============================================

def get_portfolio() -> List[Dict]:
    """ポートフォリオ一覧を取得"""
    init_database()
    return [h for h in st.session_state.portfolio if h.get('quantity', 0) > 0]


def get_holding(ticker: str) -> Optional[Dict]:
    """特定銘柄の保有情報を取得"""
    init_database()
    for h in st.session_state.portfolio:
        if h['ticker'] == ticker:
            return h.copy()
    return None


def add_or_update_holding(ticker: str, quantity: int, avg_cost: float, stop_loss: Optional[float] = None, currency: str = "JPY"):
    """保有銘柄を追加または更新"""
    init_database()
    existing = None
    for i, h in enumerate(st.session_state.portfolio):
        if h['ticker'] == ticker:
            existing = i
            break
    
    if existing is not None:
        h = st.session_state.portfolio[existing]
        total_shares = h['quantity'] + quantity
        if total_shares > 0:
            new_avg_cost = ((h['quantity'] * h['avg_cost']) + (quantity * avg_cost)) / total_shares
        else:
            new_avg_cost = avg_cost
        
        st.session_state.portfolio[existing] = {
            'id': h.get('id', existing),
            'ticker': ticker,
            'quantity': total_shares,
            'avg_cost': new_avg_cost,
            'stop_loss': stop_loss or h.get('stop_loss'),
            'currency': currency,
            'created_at': h.get('created_at'),
            'updated_at': datetime.now().isoformat()
        }
    else:
        new_id = len(st.session_state.portfolio) + 1
        st.session_state.portfolio.append({
            'id': new_id,
            'ticker': ticker,
            'quantity': quantity,
            'avg_cost': avg_cost,
            'stop_loss': stop_loss,
            'currency': currency,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
    
    save_to_cookies()


def update_stop_loss(ticker: str, stop_loss: float):
    """損切り価格を更新"""
    init_database()
    for h in st.session_state.portfolio:
        if h['ticker'] == ticker:
            h['stop_loss'] = stop_loss
            h['updated_at'] = datetime.now().isoformat()
            break
    save_to_cookies()


def sell_holding(ticker: str, quantity: int):
    """保有銘柄を売却"""
    init_database()
    for i, h in enumerate(st.session_state.portfolio):
        if h['ticker'] == ticker:
            new_quantity = max(0, h['quantity'] - quantity)
            if new_quantity == 0:
                st.session_state.portfolio.pop(i)
            else:
                h['quantity'] = new_quantity
                h['updated_at'] = datetime.now().isoformat()
            break
    save_to_cookies()


def delete_holding(ticker: str):
    """保有銘柄を削除"""
    init_database()
    st.session_state.portfolio = [h for h in st.session_state.portfolio if h['ticker'] != ticker]
    save_to_cookies()


# ============================================
# ウォッチリスト
# ============================================

def get_watchlist() -> List[str]:
    """ウォッチリストを取得"""
    init_database()
    return st.session_state.get('watchlist', [])


def add_to_watchlist(ticker: str):
    """ウォッチリストに追加"""
    init_database()
    if ticker not in st.session_state.watchlist:
        st.session_state.watchlist.append(ticker)
        save_to_cookies()


def remove_from_watchlist(ticker: str):
    """ウォッチリストから削除"""
    init_database()
    if ticker in st.session_state.watchlist:
        st.session_state.watchlist.remove(ticker)
        save_to_cookies()


# ============================================
# 取引履歴（セッションのみ、永続化しない）
# ============================================

def add_transaction(ticker: str, action: str, quantity: int, price: float):
    """取引履歴を追加"""
    init_database()
    total_amount = quantity * price
    st.session_state.transactions.append({
        'id': len(st.session_state.transactions) + 1,
        'ticker': ticker,
        'action': action,
        'quantity': quantity,
        'price': price,
        'total_amount': total_amount,
        'executed_at': datetime.now().isoformat()
    })


def get_transactions(limit: int = 20) -> List[Dict]:
    """取引履歴を取得"""
    init_database()
    sorted_txns = sorted(st.session_state.transactions, key=lambda x: x['executed_at'], reverse=True)
    return sorted_txns[:limit]
