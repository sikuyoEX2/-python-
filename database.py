"""
データベースモジュール（Turso HTTP API対応版）
/v2/pipeline エンドポイントを使用
"""
import os
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional

# Streamlit secretsまたは環境変数からTurso接続情報を取得
def get_turso_config():
    """Turso接続情報を取得（Streamlit secrets優先）"""
    try:
        import streamlit as st
        url = st.secrets.get("TURSO_DATABASE_URL", os.getenv("TURSO_DATABASE_URL", ""))
        token = st.secrets.get("TURSO_AUTH_TOKEN", os.getenv("TURSO_AUTH_TOKEN", ""))
    except:
        url = os.getenv("TURSO_DATABASE_URL", "")
        token = os.getenv("TURSO_AUTH_TOKEN", "")
    return url, token

TURSO_DATABASE_URL, TURSO_AUTH_TOKEN = get_turso_config()


def format_args(params: list) -> list:
    """パラメータをTurso API形式に変換"""
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
    return args


class TursoConnection:
    """Turso HTTP API接続クラス"""
    
    def __init__(self):
        self.base_url = TURSO_DATABASE_URL
        self.headers = {
            "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def execute(self, sql: str, params: list = None) -> dict:
        """SQLを実行"""
        request_body = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": format_args(params)}},
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
            raise Exception(f"Turso API Error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def execute_many(self, sql_list: list) -> dict:
        """複数SQLを実行"""
        reqs = []
        for sql, params in sql_list:
            reqs.append({"type": "execute", "stmt": {"sql": sql, "args": format_args(params)}})
        reqs.append({"type": "close"})
        
        request_body = {"requests": reqs}
        
        response = requests.post(
            f"{self.base_url}/v2/pipeline",
            headers=self.headers,
            json=request_body,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Turso API Error: {response.status_code} - {response.text}")
        
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
    
    def fetchone(self, sql: str, params: list = None) -> Optional[tuple]:
        """1行取得"""
        rows = self.fetchall(sql, params)
        return rows[0] if rows else None


def get_connection() -> TursoConnection:
    """データベース接続を取得"""
    return TursoConnection()


def init_database():
    """データベースを初期化"""
    conn = get_connection()
    
    statements = [
        ("CREATE TABLE IF NOT EXISTS funds (id INTEGER PRIMARY KEY, currency TEXT NOT NULL UNIQUE, amount REAL NOT NULL DEFAULT 0, updated_at TEXT)", []),
        ("CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY, ticker TEXT NOT NULL UNIQUE, quantity INTEGER NOT NULL DEFAULT 0, avg_cost REAL NOT NULL DEFAULT 0, stop_loss REAL, currency TEXT NOT NULL DEFAULT 'JPY', created_at TEXT, updated_at TEXT)", []),
        ("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, ticker TEXT NOT NULL, action TEXT NOT NULL, quantity INTEGER NOT NULL, price REAL NOT NULL, total_amount REAL NOT NULL, executed_at TEXT)", []),
        ("INSERT OR IGNORE INTO funds (currency, amount) VALUES ('JPY', 0)", []),
        ("INSERT OR IGNORE INTO funds (currency, amount) VALUES ('USD', 0)", []),
    ]
    
    conn.execute_many(statements)
    print("Database initialized")


# ============================================
# 資金管理
# ============================================

def get_funds() -> Dict[str, float]:
    """資金を取得"""
    conn = get_connection()
    rows = conn.fetchall("SELECT currency, amount FROM funds")
    return {row[0]: row[1] for row in rows}


def update_funds(currency: str, amount: float):
    """資金を更新"""
    conn = get_connection()
    conn.execute("UPDATE funds SET amount = ?, updated_at = ? WHERE currency = ?",
                 [amount, datetime.now().isoformat(), currency])


# ============================================
# ポートフォリオ管理
# ============================================

def get_portfolio() -> List[Dict]:
    """ポートフォリオ一覧を取得"""
    conn = get_connection()
    rows = conn.fetchall("SELECT id, ticker, quantity, avg_cost, stop_loss, currency, created_at FROM portfolio WHERE quantity > 0 ORDER BY created_at DESC")
    columns = ['id', 'ticker', 'quantity', 'avg_cost', 'stop_loss', 'currency', 'created_at']
    return [dict(zip(columns, row)) for row in rows]


def get_holding(ticker: str) -> Optional[Dict]:
    """特定銘柄の保有情報を取得"""
    conn = get_connection()
    row = conn.fetchone("SELECT id, ticker, quantity, avg_cost, stop_loss, currency FROM portfolio WHERE ticker = ?", [ticker])
    if row:
        columns = ['id', 'ticker', 'quantity', 'avg_cost', 'stop_loss', 'currency']
        return dict(zip(columns, row))
    return None


def add_or_update_holding(ticker: str, quantity: int, avg_cost: float, stop_loss: Optional[float] = None, currency: str = "JPY"):
    """保有銘柄を追加または更新"""
    conn = get_connection()
    existing = get_holding(ticker)
    
    if existing:
        total_shares = existing['quantity'] + quantity
        if total_shares > 0:
            new_avg_cost = ((existing['quantity'] * existing['avg_cost']) + (quantity * avg_cost)) / total_shares
        else:
            new_avg_cost = avg_cost
        
        conn.execute("UPDATE portfolio SET quantity = ?, avg_cost = ?, stop_loss = ?, updated_at = ? WHERE ticker = ?",
                     [total_shares, new_avg_cost, stop_loss or existing['stop_loss'], datetime.now().isoformat(), ticker])
    else:
        conn.execute("INSERT INTO portfolio (ticker, quantity, avg_cost, stop_loss, currency, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     [ticker, quantity, avg_cost, stop_loss, currency, datetime.now().isoformat(), datetime.now().isoformat()])


def update_stop_loss(ticker: str, stop_loss: float):
    """損切り価格を更新"""
    conn = get_connection()
    conn.execute("UPDATE portfolio SET stop_loss = ?, updated_at = ? WHERE ticker = ?",
                 [stop_loss, datetime.now().isoformat(), ticker])


def sell_holding(ticker: str, quantity: int):
    """保有銘柄を売却"""
    conn = get_connection()
    existing = get_holding(ticker)
    if existing:
        new_quantity = max(0, existing['quantity'] - quantity)
        if new_quantity == 0:
            conn.execute("DELETE FROM portfolio WHERE ticker = ?", [ticker])
        else:
            conn.execute("UPDATE portfolio SET quantity = ?, updated_at = ? WHERE ticker = ?",
                         [new_quantity, datetime.now().isoformat(), ticker])


def delete_holding(ticker: str):
    """保有銘柄を削除"""
    conn = get_connection()
    conn.execute("DELETE FROM portfolio WHERE ticker = ?", [ticker])


# ============================================
# 取引履歴
# ============================================

def add_transaction(ticker: str, action: str, quantity: int, price: float):
    """取引履歴を追加"""
    conn = get_connection()
    total_amount = quantity * price
    conn.execute("INSERT INTO transactions (ticker, action, quantity, price, total_amount, executed_at) VALUES (?, ?, ?, ?, ?, ?)",
                 [ticker, action, quantity, price, total_amount, datetime.now().isoformat()])


def get_transactions(limit: int = 20) -> List[Dict]:
    """取引履歴を取得"""
    conn = get_connection()
    rows = conn.fetchall(f"SELECT id, ticker, action, quantity, price, total_amount, executed_at FROM transactions ORDER BY executed_at DESC LIMIT {limit}")
    columns = ['id', 'ticker', 'action', 'quantity', 'price', 'total_amount', 'executed_at']
    return [dict(zip(columns, row)) for row in rows]


# 初期化
try:
    init_database()
except Exception as e:
    print(f"Database init error: {e}")
