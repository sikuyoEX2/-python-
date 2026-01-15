"""
データベースモジュール（ハイブリッド永続化版）
- Streamlit Cloud: Turso HTTP API
- ローカル: JSONファイル
"""
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional
import json
import os
from pathlib import Path


# ============================================
# 設定
# ============================================

def get_turso_config():
    """Turso接続情報を取得"""
    url = ""
    token = ""
    
    try:
        # Streamlit secretsから取得
        if hasattr(st, 'secrets'):
            url = st.secrets.get("TURSO_DATABASE_URL", "")
            token = st.secrets.get("TURSO_AUTH_TOKEN", "")
    except:
        pass
    
    # 環境変数からフォールバック
    if not url:
        url = os.getenv("TURSO_DATABASE_URL", "")
    if not token:
        token = os.getenv("TURSO_AUTH_TOKEN", "")
    
    return url, token


def is_turso_available():
    """Tursoが利用可能かチェック"""
    url, token = get_turso_config()
    return bool(url and token)


# ============================================
# Turso HTTP API
# ============================================

class TursoConnection:
    """Turso HTTP API接続クラス"""
    
    def __init__(self):
        url, token = get_turso_config()
        self.base_url = url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def execute(self, sql: str, params: list = None) -> dict:
        """SQLを実行"""
        import requests
        
        args = []
        for p in (params or []):
            if p is None:
                args.append({"type": "null"})
            elif isinstance(p, str):
                args.append({"type": "text", "value": p})
            elif isinstance(p, int):
                args.append({"type": "integer", "value": str(p)})
            elif isinstance(p, float):
                args.append({"type": "float", "value": str(p)})
            else:
                args.append({"type": "text", "value": str(p)})
        
        request_body = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": args}},
                {"type": "close"}
            ]
        }
        
        response = requests.post(
            f"{self.base_url}/v2/pipeline",
            headers=self.headers,
            json=request_body,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Turso API Error: {response.status_code}")
        
        return response.json()
    
    def fetchall(self, sql: str, params: list = None) -> List[tuple]:
        """SELECT結果を取得"""
        result = self.execute(sql, params)
        
        try:
            results = result.get("results", [])
            if results and len(results) > 0:
                first_result = results[0]
                if first_result.get("type") == "ok":
                    response_data = first_result.get("response", {})
                    result_data = response_data.get("result", {})
                    rows = result_data.get("rows", [])
                    
                    extracted = []
                    for row in rows:
                        values = []
                        for cell in row:
                            if cell.get("type") == "null":
                                values.append(None)
                            elif cell.get("type") == "integer":
                                values.append(int(cell.get("value")))
                            elif cell.get("type") == "float":
                                values.append(float(cell.get("value")))
                            else:
                                values.append(cell.get("value"))
                        extracted.append(tuple(values))
                    return extracted
        except Exception as e:
            print(f"Parse error: {e}")
        
        return []


# ============================================
# ローカルJSON永続化
# ============================================

DATA_DIR = Path(__file__).parent / ".data"
FUNDS_FILE = DATA_DIR / "funds.json"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"


def ensure_data_dir():
    """データディレクトリを作成"""
    DATA_DIR.mkdir(exist_ok=True)


def load_json_file(filepath: Path, default):
    """JSONファイルを読み込み"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return default


def save_json_file(filepath: Path, data):
    """JSONファイルに保存"""
    ensure_data_dir()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


# ============================================
# 初期化
# ============================================

def init_database():
    """データベースを初期化"""
    if 'db_initialized' in st.session_state:
        return
    
    st.session_state.db_initialized = True
    
    if is_turso_available():
        # Tursoで初期化
        try:
            conn = TursoConnection()
            conn.execute("CREATE TABLE IF NOT EXISTS funds (id INTEGER PRIMARY KEY, currency TEXT UNIQUE, amount REAL DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY, ticker TEXT UNIQUE, quantity INTEGER DEFAULT 0, avg_cost REAL DEFAULT 0, stop_loss REAL, currency TEXT DEFAULT 'JPY', created_at TEXT, updated_at TEXT)")
            conn.execute("INSERT OR IGNORE INTO funds (currency, amount) VALUES ('JPY', 0)")
            conn.execute("INSERT OR IGNORE INTO funds (currency, amount) VALUES ('USD', 0)")
            st.session_state.use_turso = True
            print("Using Turso database")
        except Exception as e:
            print(f"Turso init failed: {e}")
            st.session_state.use_turso = False
    else:
        # ローカルJSON
        st.session_state.use_turso = False
        ensure_data_dir()
        st.session_state.funds = load_json_file(FUNDS_FILE, {'JPY': 0.0, 'USD': 0.0})
        st.session_state.portfolio = load_json_file(PORTFOLIO_FILE, [])
        st.session_state.watchlist = load_json_file(WATCHLIST_FILE, [])
        print("Using local JSON storage")
    
    if 'transactions' not in st.session_state:
        st.session_state.transactions = []


def sync_to_localstorage():
    """後方互換性のため"""
    pass


def render_data_loader():
    """後方互換性のため"""
    pass


# ============================================
# 資金管理
# ============================================

def get_funds() -> Dict[str, float]:
    """資金を取得"""
    init_database()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            rows = conn.fetchall("SELECT currency, amount FROM funds")
            return {row[0]: row[1] for row in rows}
        except:
            return {'JPY': 0.0, 'USD': 0.0}
    else:
        return st.session_state.get('funds', {'JPY': 0.0, 'USD': 0.0}).copy()


def update_funds(currency: str, amount: float):
    """資金を更新"""
    init_database()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            conn.execute("UPDATE funds SET amount = ? WHERE currency = ?", [amount, currency])
        except:
            pass
    else:
        st.session_state.funds[currency] = amount
        save_json_file(FUNDS_FILE, st.session_state.funds)


# ============================================
# ポートフォリオ管理
# ============================================

def get_portfolio() -> List[Dict]:
    """ポートフォリオ一覧を取得"""
    init_database()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            rows = conn.fetchall("SELECT id, ticker, quantity, avg_cost, stop_loss, currency, created_at FROM portfolio WHERE quantity > 0")
            columns = ['id', 'ticker', 'quantity', 'avg_cost', 'stop_loss', 'currency', 'created_at']
            return [dict(zip(columns, row)) for row in rows]
        except:
            return []
    else:
        return [h for h in st.session_state.get('portfolio', []) if h.get('quantity', 0) > 0]


def get_holding(ticker: str) -> Optional[Dict]:
    """特定銘柄の保有情報を取得"""
    init_database()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            rows = conn.fetchall("SELECT id, ticker, quantity, avg_cost, stop_loss, currency FROM portfolio WHERE ticker = ?", [ticker])
            if rows:
                columns = ['id', 'ticker', 'quantity', 'avg_cost', 'stop_loss', 'currency']
                return dict(zip(columns, rows[0]))
        except:
            pass
        return None
    else:
        for h in st.session_state.get('portfolio', []):
            if h['ticker'] == ticker:
                return h.copy()
        return None


def add_or_update_holding(ticker: str, quantity: int, avg_cost: float, stop_loss: Optional[float] = None, currency: str = "JPY"):
    """保有銘柄を追加または更新"""
    init_database()
    now = datetime.now().isoformat()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            existing = get_holding(ticker)
            
            if existing:
                total = existing['quantity'] + quantity
                new_avg = ((existing['quantity'] * existing['avg_cost']) + (quantity * avg_cost)) / total if total > 0 else avg_cost
                sl = stop_loss or existing.get('stop_loss')
                conn.execute("UPDATE portfolio SET quantity = ?, avg_cost = ?, stop_loss = ?, updated_at = ? WHERE ticker = ?",
                           [total, new_avg, sl, now, ticker])
            else:
                conn.execute("INSERT INTO portfolio (ticker, quantity, avg_cost, stop_loss, currency, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           [ticker, quantity, avg_cost, stop_loss, currency, now, now])
        except:
            pass
    else:
        portfolio = st.session_state.get('portfolio', [])
        existing_idx = None
        for i, h in enumerate(portfolio):
            if h['ticker'] == ticker:
                existing_idx = i
                break
        
        if existing_idx is not None:
            h = portfolio[existing_idx]
            total = h['quantity'] + quantity
            new_avg = ((h['quantity'] * h['avg_cost']) + (quantity * avg_cost)) / total if total > 0 else avg_cost
            portfolio[existing_idx] = {
                'id': h.get('id', existing_idx),
                'ticker': ticker,
                'quantity': total,
                'avg_cost': new_avg,
                'stop_loss': stop_loss or h.get('stop_loss'),
                'currency': currency,
                'created_at': h.get('created_at'),
                'updated_at': now
            }
        else:
            portfolio.append({
                'id': len(portfolio) + 1,
                'ticker': ticker,
                'quantity': quantity,
                'avg_cost': avg_cost,
                'stop_loss': stop_loss,
                'currency': currency,
                'created_at': now,
                'updated_at': now
            })
        
        st.session_state.portfolio = portfolio
        save_json_file(PORTFOLIO_FILE, portfolio)


def update_stop_loss(ticker: str, stop_loss: float):
    """損切り価格を更新"""
    init_database()
    now = datetime.now().isoformat()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            conn.execute("UPDATE portfolio SET stop_loss = ?, updated_at = ? WHERE ticker = ?", [stop_loss, now, ticker])
        except:
            pass
    else:
        for h in st.session_state.get('portfolio', []):
            if h['ticker'] == ticker:
                h['stop_loss'] = stop_loss
                h['updated_at'] = now
                break
        save_json_file(PORTFOLIO_FILE, st.session_state.portfolio)


def sell_holding(ticker: str, quantity: int):
    """保有銘柄を売却"""
    init_database()
    now = datetime.now().isoformat()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            existing = get_holding(ticker)
            if existing:
                new_qty = max(0, existing['quantity'] - quantity)
                if new_qty == 0:
                    conn.execute("DELETE FROM portfolio WHERE ticker = ?", [ticker])
                else:
                    conn.execute("UPDATE portfolio SET quantity = ?, updated_at = ? WHERE ticker = ?", [new_qty, now, ticker])
        except:
            pass
    else:
        portfolio = st.session_state.get('portfolio', [])
        for i, h in enumerate(portfolio):
            if h['ticker'] == ticker:
                new_qty = max(0, h['quantity'] - quantity)
                if new_qty == 0:
                    portfolio.pop(i)
                else:
                    h['quantity'] = new_qty
                    h['updated_at'] = now
                break
        st.session_state.portfolio = portfolio
        save_json_file(PORTFOLIO_FILE, portfolio)


def delete_holding(ticker: str):
    """保有銘柄を削除"""
    init_database()
    
    if st.session_state.get('use_turso'):
        try:
            conn = TursoConnection()
            conn.execute("DELETE FROM portfolio WHERE ticker = ?", [ticker])
        except:
            pass
    else:
        st.session_state.portfolio = [h for h in st.session_state.get('portfolio', []) if h['ticker'] != ticker]
        save_json_file(PORTFOLIO_FILE, st.session_state.portfolio)


# ============================================
# ウォッチリスト（ローカルのみ）
# ============================================

def get_watchlist() -> List[str]:
    """ウォッチリストを取得"""
    init_database()
    return st.session_state.get('watchlist', [])


def add_to_watchlist(ticker: str):
    """ウォッチリストに追加"""
    init_database()
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []
    if ticker not in st.session_state.watchlist:
        st.session_state.watchlist.append(ticker)
        if not st.session_state.get('use_turso'):
            save_json_file(WATCHLIST_FILE, st.session_state.watchlist)


def remove_from_watchlist(ticker: str):
    """ウォッチリストから削除"""
    init_database()
    if ticker in st.session_state.get('watchlist', []):
        st.session_state.watchlist.remove(ticker)
        if not st.session_state.get('use_turso'):
            save_json_file(WATCHLIST_FILE, st.session_state.watchlist)


# ============================================
# 取引履歴（セッションのみ）
# ============================================

def add_transaction(ticker: str, action: str, quantity: int, price: float):
    """取引履歴を追加"""
    init_database()
    if 'transactions' not in st.session_state:
        st.session_state.transactions = []
    st.session_state.transactions.append({
        'id': len(st.session_state.transactions) + 1,
        'ticker': ticker,
        'action': action,
        'quantity': quantity,
        'price': price,
        'total_amount': quantity * price,
        'executed_at': datetime.now().isoformat()
    })


def get_transactions(limit: int = 20) -> List[Dict]:
    """取引履歴を取得"""
    init_database()
    txns = st.session_state.get('transactions', [])
    return sorted(txns, key=lambda x: x['executed_at'], reverse=True)[:limit]
