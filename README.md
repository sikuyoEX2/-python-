# 株価監視・売買シグナル通知Webアプリ

トレンドフォロー戦略に基づく売買シグナルを自動検出し、通知するWebアプリケーションです。

## 🚀 クイックスタート

```powershell
cd d:\デスクトップ\python-株\stock_signal_app
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

ブラウザで `http://localhost:8501` を開きます。

## 📊 機能

### シグナル判定
| 条件 | 買い | 売り |
|------|------|------|
| 環境認識 | 終値 > 200EMA（両時間足） | 終値 < 200EMA |
| セットアップ | 20EMA付近 or RSI < 40 | 20EMA付近 or RSI > 60 |
| トリガー | 下ヒゲピンバー / 陽線包み足 | 上ヒゲピンバー / 陰線包み足 |

### 主な機能
- **ローソク足チャート表示**: EMA(20, 200) + RSI付き
- **シグナルマーカー**: チャート上に買い/売りシグナルを表示
- **リスクリワード計算**: 損切り・利確目標を自動提案（RR 1:2）
- **ウォッチリスト**: 複数銘柄を登録・一括分析
- **通知機能**: Discord/LINE Webhook、ブラウザ通知

## 🔔 通知設定

### Discord Webhook
1. Discordサーバーで「サーバー設定」→「連携サービス」→「ウェブフック」
2. 「新しいウェブフック」を作成してURLをコピー
3. アプリのサイドバー「通知設定」にURLを貼り付け

### LINE Notify
1. https://notify-bot.line.me/ にアクセス
2. トークンを発行
3. アプリのサイドバー「通知設定」にトークンを貼り付け

## 📁 ファイル構成

```
stock_signal_app/
├── app.py              # メインアプリ（Streamlit）
├── data_fetcher.py     # yfinance データ取得
├── indicators.py       # EMA, RSI 計算
├── patterns.py         # ローソク足パターン判定
├── signals.py          # シグナル判定ロジック
├── chart.py            # Plotlyチャート生成
├── notifications.py    # 通知機能
└── requirements.txt    # 依存関係
```

## 📈 対応銘柄

| 市場 | 形式 | 例 |
|------|------|-----|
| 米国株 | ティッカーのみ | `AAPL`, `NVDA`, `GOOGL` |
| 日本株 | コード + `.T` | `7203.T`, `9984.T` |

## ⚠️ 注意事項

- このツールは分析・監視用であり、自動売買機能はありません
- 投資判断は自己責任で行ってください
- yfinanceの制限により、15分足は直近5日分のみ取得可能です
