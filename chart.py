"""
チャート生成モジュール
Plotlyでインタラクティブなローソク足チャートを描画
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def create_candlestick_chart(
    df: pd.DataFrame,
    ticker: str,
    show_signals: bool = True
) -> go.Figure:
    """
    ローソク足チャートを生成（EMA、RSI、シグナルマーカー付き）
    
    Args:
        df: 指標・パターンが追加されたDataFrame
        ticker: 銘柄コード
        show_signals: シグナルマーカーを表示するか
    
    Returns:
        Plotly Figure オブジェクト
    """
    # サブプロット作成（上: ローソク足、下: RSI）
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{ticker} - ローソク足チャート', 'RSI (14)')
    )
    
    # ローソク足
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    # EMA 20
    if 'ema_20' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['ema_20'],
                mode='lines',
                name='EMA 20',
                line=dict(color='#2196F3', width=1.5)
            ),
            row=1, col=1
        )
    
    # EMA 200
    if 'ema_200' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['ema_200'],
                mode='lines',
                name='EMA 200',
                line=dict(color='#FF9800', width=2)
            ),
            row=1, col=1
        )
    
    # シグナルマーカー
    if show_signals:
        # 買いシグナル（下ヒゲピンバー or 陽線包み足）
        buy_signals = df[
            (df.get('pin_bar', 'none') == 'bullish_pin') |
            (df.get('engulfing', 'none') == 'bullish_engulfing')
        ]
        if not buy_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals['low'] * 0.998,
                    mode='markers',
                    name='買いシグナル',
                    marker=dict(
                        symbol='triangle-up',
                        size=15,
                        color='#00E676',
                        line=dict(width=1, color='white')
                    ),
                    hovertemplate='買いシグナル<br>%{x}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 売りシグナル（上ヒゲピンバー or 陰線包み足）
        sell_signals = df[
            (df.get('pin_bar', 'none') == 'bearish_pin') |
            (df.get('engulfing', 'none') == 'bearish_engulfing')
        ]
        if not sell_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals['high'] * 1.002,
                    mode='markers',
                    name='売りシグナル',
                    marker=dict(
                        symbol='triangle-down',
                        size=15,
                        color='#FF5252',
                        line=dict(width=1, color='white')
                    ),
                    hovertemplate='売りシグナル<br>%{x}<extra></extra>'
                ),
                row=1, col=1
            )
    
    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['rsi'],
                mode='lines',
                name='RSI',
                line=dict(color='#9C27B0', width=1.5)
            ),
            row=2, col=1
        )
        
        # RSI オーバーボート/オーバーソールドライン
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)
    
    # レイアウト設定
    fig.update_layout(
        height=700,
        template='plotly_dark',
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    fig.update_yaxes(title_text="価格", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    
    return fig


def create_simple_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    シンプルなローソク足チャート（指標なし）
    
    Args:
        df: OHLCデータ
        ticker: 銘柄コード
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC'
        )
    ])
    
    fig.update_layout(
        title=f'{ticker} チャート',
        template='plotly_dark',
        height=500,
        xaxis_rangeslider_visible=False
    )
    
    return fig
