"""
機械学習エンジンモジュール
LightGBMを使用した株価騰落予測
"""
import os
from pathlib import Path
from typing import Optional, Dict, List
import pandas as pd
import numpy as np


class StockPredictor:
    """株価騰落予測クラス"""
    
    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: 学習済みモデルのパス
        """
        self.model = None
        self.feature_names = ['rsi', 'ema_ratio', 'volume_ratio', 'sentiment', 'price_change_5d']
        
        if model_path is None:
            model_path = Path(__file__).parent / 'models' / 'lgbm_model.pkl'
        
        self._load_model(model_path)
    
    def _load_model(self, model_path):
        """モデルをロード"""
        try:
            import joblib
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                print(f"Model loaded from {model_path}")
            else:
                print(f"Model not found: {model_path}")
        except ImportError:
            print("joblib not installed")
        except Exception as e:
            print(f"Model load error: {e}")
    
    def is_available(self) -> bool:
        """モデルが利用可能かどうか"""
        return self.model is not None
    
    def prepare_features(self, df: pd.DataFrame, sentiment_score: int = 50) -> pd.DataFrame:
        """
        テクニカルデータと感情スコアから特徴量を作成
        
        Args:
            df: OHLCVデータ（EMA, RSI計算済み）
            sentiment_score: 感情スコア (0-100)
        
        Returns:
            特徴量DataFrame
        """
        if df.empty or len(df) < 5:
            return pd.DataFrame()
        
        latest = df.iloc[-1]
        
        # 特徴量作成
        features = {}
        
        # RSI
        features['rsi'] = latest.get('rsi', 50)
        
        # EMA比率（現在価格 / EMA200）
        ema_200 = latest.get('ema_200', latest['close'])
        features['ema_ratio'] = (latest['close'] / ema_200) if ema_200 > 0 else 1.0
        
        # 出来高比率（直近出来高 / 5日平均出来高）
        if 'volume' in df.columns and len(df) >= 5:
            avg_volume = df['volume'].tail(5).mean()
            features['volume_ratio'] = (latest['volume'] / avg_volume) if avg_volume > 0 else 1.0
        else:
            features['volume_ratio'] = 1.0
        
        # 感情スコア（正規化: 0-1）
        features['sentiment'] = sentiment_score / 100.0
        
        # 5日間の価格変化率
        if len(df) >= 5:
            price_5d_ago = df['close'].iloc[-5]
            features['price_change_5d'] = (latest['close'] - price_5d_ago) / price_5d_ago if price_5d_ago > 0 else 0
        else:
            features['price_change_5d'] = 0
        
        return pd.DataFrame([features])
    
    def predict(self, df: pd.DataFrame, sentiment_score: int = 50) -> Dict:
        """
        株価騰落を予測
        
        Args:
            df: OHLCVデータ
            sentiment_score: 感情スコア (0-100)
        
        Returns:
            予測結果の辞書
        """
        # モデルがない場合はシンプルな推定
        if not self.is_available():
            return self._simple_prediction(df, sentiment_score)
        
        # 特徴量作成
        features = self.prepare_features(df, sentiment_score)
        
        if features.empty:
            return {'prediction': 0, 'confidence': 0, 'direction': '不明'}
        
        try:
            # 予測実行
            prediction = self.model.predict(features)[0]
            
            # 確率が取得できる場合
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(features)[0]
                confidence = max(proba) * 100
            else:
                confidence = 50
            
            # 方向判定
            if prediction > 0.02:
                direction = "📈 上昇予測"
            elif prediction < -0.02:
                direction = "📉 下落予測"
            else:
                direction = "➡️ 横ばい予測"
            
            return {
                'prediction': float(prediction),
                'confidence': confidence,
                'direction': direction
            }
        except Exception as e:
            print(f"Prediction error: {e}")
            return {'prediction': 0, 'confidence': 0, 'direction': 'エラー'}
    
    def _simple_prediction(self, df: pd.DataFrame, sentiment_score: int) -> Dict:
        """
        モデルなしでのシンプルな予測（テクニカル指標ベース）
        """
        if df.empty:
            return {'prediction': 0, 'confidence': 0, 'direction': '不明'}
        
        latest = df.iloc[-1]
        
        # RSIベースのスコア
        rsi = latest.get('rsi', 50)
        rsi_score = 50 - rsi  # RSI低い = 上昇余地あり
        
        # EMAベースのスコア
        ema_200 = latest.get('ema_200', latest['close'])
        ema_score = 25 if latest['close'] > ema_200 else -25
        
        # 感情スコア
        sentiment_contribution = (sentiment_score - 50) * 0.5
        
        # 総合スコア
        total_score = rsi_score + ema_score + sentiment_contribution
        
        # 予測（-1 ~ 1 に正規化）
        prediction = max(-1, min(1, total_score / 100))
        
        # 方向判定
        if prediction > 0.1:
            direction = "📈 上昇示唆"
        elif prediction < -0.1:
            direction = "📉 下落示唆"
        else:
            direction = "➡️ 中立"
        
        return {
            'prediction': prediction,
            'confidence': abs(prediction) * 50 + 25,
            'direction': direction,
            'note': '※シンプル推定（MLモデル未使用）'
        }


def train_model(ticker_list: List[str], output_path: str = 'models/lgbm_model.pkl'):
    """
    学習用スクリプト（ローカル実行用）
    
    Args:
        ticker_list: 学習データの銘柄リスト
        output_path: モデル保存先
    """
    try:
        import lightgbm as lgb
        from sklearn.model_selection import train_test_split
        import joblib
        import yfinance as yf
    except ImportError as e:
        print(f"Required package not installed: {e}")
        return
    
    print("Collecting training data...")
    
    all_features = []
    all_targets = []
    
    for ticker in ticker_list:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            
            if len(df) < 50:
                continue
            
            # 指標計算
            df['rsi'] = calculate_rsi(df['Close'], 14)
            df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            df['ema_ratio'] = df['Close'] / df['ema_200']
            df['volume_ratio'] = df['Volume'] / df['Volume'].rolling(5).mean()
            df['price_change_5d'] = df['Close'].pct_change(5)
            
            # ターゲット: 翌日リターン
            df['target'] = df['Close'].shift(-1) / df['Close'] - 1
            
            # 感情スコアはダミー（50固定）
            df['sentiment'] = 0.5
            
            # NaN除去
            df = df.dropna()
            
            # 特徴量とターゲット
            feature_cols = ['rsi', 'ema_ratio', 'volume_ratio', 'sentiment', 'price_change_5d']
            all_features.append(df[feature_cols])
            all_targets.append(df['target'])
            
            print(f"  {ticker}: {len(df)} samples")
        except Exception as e:
            print(f"  {ticker}: Error - {e}")
    
    if not all_features:
        print("No training data collected")
        return
    
    # データ結合
    X = pd.concat(all_features)
    y = pd.concat(all_targets)
    
    print(f"Total samples: {len(X)}")
    
    # 学習/テスト分割
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # LightGBM学習
    train_data = lgb.Dataset(X_train, label=y_train)
    valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'verbose': -1
    }
    
    print("Training LightGBM model...")
    model = lgb.train(
        params,
        train_data,
        num_boost_round=100,
        valid_sets=[valid_data],
        callbacks=[lgb.early_stopping(10)]
    )
    
    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    print(f"Model saved to {output_path}")


def calculate_rsi(prices, period=14):
    """RSI計算（学習用）"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


if __name__ == "__main__":
    # ローカルで実行してモデルを学習
    sample_tickers = [
        "7203.T", "6758.T", "9984.T", "6861.T", "8306.T",
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"
    ]
    train_model(sample_tickers)
