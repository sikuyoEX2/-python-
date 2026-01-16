"""
初心者向け用語解説モジュール（図表付き）
"""
import streamlit as st
import plotly.graph_objects as go


def create_candlestick_diagram(candle_type: str) -> go.Figure:
    """ローソク足の図を生成"""
    fig = go.Figure()
    
    if candle_type == "bullish":
        fig.add_trace(go.Candlestick(
            x=[1], open=[100], high=[120], low=[95], close=[115],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a'
        ))
        fig.update_layout(title="陽線（上昇）", height=200)
    elif candle_type == "bearish":
        fig.add_trace(go.Candlestick(
            x=[1], open=[115], high=[120], low=[95], close=[100],
            decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
        ))
        fig.update_layout(title="陰線（下落）", height=200)
    elif candle_type == "pin_bar_bullish":
        fig.add_trace(go.Candlestick(
            x=[1], open=[108], high=[112], low=[90], close=[110],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a'
        ))
        fig.update_layout(title="下ヒゲピンバー", height=200)
    elif candle_type == "pin_bar_bearish":
        fig.add_trace(go.Candlestick(
            x=[1], open=[102], high=[120], low=[98], close=[100],
            decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
        ))
        fig.update_layout(title="上ヒゲピンバー", height=200)
    elif candle_type == "engulfing_bullish":
        fig.add_trace(go.Candlestick(
            x=[1, 2], 
            open=[110, 95], high=[112, 118], low=[100, 93], close=[102, 115],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
            decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
        ))
        fig.update_layout(title="陽線包み足", height=200)
    elif candle_type == "engulfing_bearish":
        fig.add_trace(go.Candlestick(
            x=[1, 2], 
            open=[100, 115], high=[110, 118], low=[98, 92], close=[108, 95],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
            decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
        ))
        fig.update_layout(title="陰線包み足", height=200)
    elif candle_type == "doji":
        fig.add_trace(go.Candlestick(
            x=[1], open=[105], high=[115], low=[95], close=[105.5],
            increasing_line_color='#9e9e9e', increasing_fillcolor='#9e9e9e'
        ))
        fig.update_layout(title="十字線", height=200)
    elif candle_type == "morning_star":
        fig.add_trace(go.Candlestick(
            x=[1, 2, 3], 
            open=[115, 100, 102], high=[118, 103, 118], low=[98, 98, 100], close=[100, 101, 115],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
            decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
        ))
        fig.update_layout(title="三川明けの明星", height=200)
    elif candle_type == "evening_star":
        fig.add_trace(go.Candlestick(
            x=[1, 2, 3], 
            open=[100, 115, 113], high=[118, 118, 115], low=[98, 112, 95], close=[115, 114, 98],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
            decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
        ))
        fig.update_layout(title="三川宵の明星", height=200)
    elif candle_type == "harami":
        fig.add_trace(go.Candlestick(
            x=[1, 2], 
            open=[115, 103], high=[118, 107], low=[98, 100], close=[100, 105],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
            decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
        ))
        fig.update_layout(title="はらみ線", height=200)
    elif candle_type == "structure":
        fig.add_trace(go.Candlestick(
            x=[1], open=[100], high=[120], low=[90], close=[115],
            increasing_line_color='#26a69a', increasing_fillcolor='#26a69a'
        ))
        fig.add_annotation(x=1, y=120, text="高値", showarrow=True, arrowhead=2, ax=40, ay=0)
        fig.add_annotation(x=1, y=90, text="安値", showarrow=True, arrowhead=2, ax=40, ay=0)
        fig.add_annotation(x=1, y=115, text="終値", showarrow=True, arrowhead=2, ax=-40, ay=-20)
        fig.add_annotation(x=1, y=100, text="始値", showarrow=True, arrowhead=2, ax=-40, ay=20)
        fig.update_layout(title="ローソク足の構造", height=250)
    
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        showlegend=False,
        xaxis=dict(showticklabels=False),
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig


def create_trend_diagram(trend_type: str) -> go.Figure:
    """トレンドの図を生成"""
    fig = go.Figure()
    
    if trend_type == "uptrend":
        x = list(range(10))
        y = [100, 105, 103, 110, 108, 115, 112, 120, 118, 125]
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='価格', line=dict(color='#26a69a')))
        fig.add_trace(go.Scatter(x=x, y=[98, 100, 102, 104, 106, 108, 110, 112, 114, 116], 
                                  mode='lines', name='EMA200', line=dict(color='#FF9800', dash='dash')))
        fig.update_layout(title="上昇トレンド（価格 > EMA）", height=200)
    elif trend_type == "downtrend":
        x = list(range(10))
        y = [125, 120, 122, 115, 118, 110, 113, 105, 108, 100]
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='価格', line=dict(color='#ef5350')))
        fig.add_trace(go.Scatter(x=x, y=[127, 125, 123, 121, 119, 117, 115, 113, 111, 109], 
                                  mode='lines', name='EMA200', line=dict(color='#FF9800', dash='dash')))
        fig.update_layout(title="下落トレンド（価格 < EMA）", height=200)
    elif trend_type == "pullback":
        x = list(range(10))
        y = [100, 108, 115, 112, 108, 106, 110, 118, 125, 130]
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='価格', line=dict(color='#26a69a')))
        fig.add_vrect(x0=3.5, x1=5.5, fillcolor="yellow", opacity=0.3, line_width=0)
        fig.add_annotation(x=4.5, y=104, text="押し目", showarrow=False, font=dict(size=14))
        fig.update_layout(title="押し目（買いチャンス）", height=200)
    elif trend_type == "rally":
        x = list(range(10))
        y = [130, 122, 115, 118, 122, 124, 120, 112, 105, 100]
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='価格', line=dict(color='#ef5350')))
        fig.add_vrect(x0=3.5, x1=5.5, fillcolor="yellow", opacity=0.3, line_width=0)
        fig.add_annotation(x=4.5, y=126, text="戻り", showarrow=False, font=dict(size=14))
        fig.update_layout(title="戻り（売りチャンス）", height=200)
    
    fig.update_layout(
        template='plotly_dark',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(showticklabels=False),
        margin=dict(l=10, r=10, t=60, b=10)
    )
    return fig


def create_rsi_diagram() -> go.Figure:
    """RSIの図を生成"""
    fig = go.Figure()
    
    x = list(range(20))
    rsi = [50, 55, 62, 68, 75, 78, 72, 65, 58, 45, 35, 28, 25, 30, 40, 52, 60, 65, 58, 50]
    
    fig.add_trace(go.Scatter(x=x, y=rsi, mode='lines', name='RSI', line=dict(color='#9C27B0', width=2)))
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="買われすぎ (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="売られすぎ (30)")
    fig.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor="green", opacity=0.1, line_width=0)
    
    fig.update_layout(
        title="RSI（相対力指数）",
        template='plotly_dark',
        height=200,
        yaxis=dict(range=[0, 100]),
        xaxis=dict(showticklabels=False),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False
    )
    return fig


def create_risk_reward_diagram() -> go.Figure:
    """リスクリワードの図を生成"""
    fig = go.Figure()
    
    fig.add_shape(type="line", x0=0, x1=1, y0=100, y1=100, line=dict(color="blue", width=2))
    fig.add_shape(type="line", x0=0, x1=1, y0=95, y1=95, line=dict(color="red", width=2, dash="dash"))
    fig.add_shape(type="line", x0=0, x1=1, y0=110, y1=110, line=dict(color="green", width=2, dash="dash"))
    
    fig.add_annotation(x=1.05, y=100, text="エントリー: 100", showarrow=False, xanchor="left")
    fig.add_annotation(x=1.05, y=95, text="損切り: 95", showarrow=False, xanchor="left", font=dict(color="red"))
    fig.add_annotation(x=1.05, y=110, text="利確: 110", showarrow=False, xanchor="left", font=dict(color="green"))
    
    fig.add_shape(type="rect", x0=0.4, x1=0.6, y0=95, y1=100, fillcolor="red", opacity=0.3)
    fig.add_shape(type="rect", x0=0.4, x1=0.6, y0=100, y1=110, fillcolor="green", opacity=0.3)
    fig.add_annotation(x=0.5, y=97.5, text="リスク", showarrow=False)
    fig.add_annotation(x=0.5, y=105, text="リワード", showarrow=False)
    
    fig.update_layout(
        title="リスクリワード 1:2",
        template='plotly_dark',
        height=200,
        yaxis=dict(range=[90, 115]),
        xaxis=dict(showticklabels=False, range=[0, 1.3]),
        margin=dict(l=10, r=80, t=40, b=10),
        showlegend=False
    )
    return fig


def render_glossary_page():
    """用語解説ページをレンダリング"""
    
    st.title("📚 初心者向け用語解説")
    st.markdown("株式投資・テクニカル分析で使われる用語を図解付きで解説します。")
    
    with st.sidebar:
        st.subheader("📂 カテゴリ")
        category = st.radio(
            "カテゴリを選択",
            ["🕯️ ローソク足の基本", "📊 テクニカル指標", "📈 チャートパターン", "🚦 シグナル用語", "💹 トレード用語"],
            label_visibility="collapsed"
        )
    
    if category == "🕯️ ローソク足の基本":
        render_candlestick_basics()
    elif category == "📊 テクニカル指標":
        render_technical_indicators()
    elif category == "📈 チャートパターン":
        render_chart_patterns()
    elif category == "🚦 シグナル用語":
        render_signal_terms()
    elif category == "💹 トレード用語":
        render_trade_terms()


def render_candlestick_basics():
    """ローソク足の基本用語"""
    
    st.subheader("🕯️ ローソク足の基本")
    
    with st.expander("**ローソク足の構造**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("structure"), use_container_width=True)
        st.write("一定期間の値動きを1本の棒で表したもの。始値・終値・高値・安値の4つの価格情報を含む。")
        st.info("💡 日本発祥のチャート表示方法で、世界中で使われています。")
    
    with st.expander("**陽線（ようせん）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("bullish"), use_container_width=True)
        st.write("終値が始値より高い（上昇した）ローソク足。緑や白で表示されることが多い。")
        st.info("💡 買いの勢いが強かったことを示します。")
    
    with st.expander("**陰線（いんせん）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("bearish"), use_container_width=True)
        st.write("終値が始値より低い（下落した）ローソク足。赤や黒で表示されることが多い。")
        st.info("💡 売りの勢いが強かったことを示します。")
    
    with st.expander("**始値・終値・高値・安値**", expanded=False):
        st.markdown("""
        | 用語 | 英語 | 説明 |
        |------|------|------|
        | 始値（はじめね） | Open | その期間で最初についた価格 |
        | 終値（おわりね） | Close | その期間で最後についた価格（最重要）|
        | 高値（たかね） | High | その期間で最も高かった価格 |
        | 安値（やすね） | Low | その期間で最も安かった価格 |
        """)
        st.info("💡 終値は最も重要視される価格です。")
    
    with st.expander("**実体とヒゲ**", expanded=False):
        st.markdown("""
        ```
             ┃ ← 上ヒゲ（高値まで）
           ┏━┻━┓
           ┃   ┃ ← 実体（始値〜終値）
           ┗━┳━┛
             ┃ ← 下ヒゲ（安値まで）
        ```
        """)
        st.write("**実体**: 始値と終値で囲まれた太い部分。実体が長いほどその方向への勢いが強い。")
        st.write("**ヒゲ**: 実体から上下に伸びる細い線。一時的にその方向に動いたが押し戻されたことを意味する。")
        st.info("💡 長いヒゲは反転のサインになることがあります。")
    
    with st.expander("**時間足**", expanded=False):
        st.markdown("""
        | 時間足 | 1本の期間 | 用途 |
        |--------|----------|------|
        | 1分足 | 1分 | スキャルピング |
        | 15分足 | 15分 | デイトレード |
        | 1時間足 | 1時間 | デイトレード |
        | 4時間足 | 4時間 | スイングトレード |
        | 日足 | 1日 | スイングトレード |
        """)
        st.info("💡 短い時間足ほど細かい動き、長い時間足ほど大きなトレンドが見えます。")


def render_technical_indicators():
    """テクニカル指標の用語"""
    
    st.subheader("📊 テクニカル指標")
    
    with st.expander("**EMA（指数移動平均線）**", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_trend_diagram("uptrend"), use_container_width=True)
        with col2:
            st.plotly_chart(create_trend_diagram("downtrend"), use_container_width=True)
        st.write("直近の価格により大きな重みを付けて計算した移動平均線。")
        st.info("💡 価格がEMAより上→上昇トレンド、下→下落トレンド")
    
    with st.expander("**EMA 20（短期）**", expanded=False):
        st.plotly_chart(create_trend_diagram("pullback"), use_container_width=True)
        st.write("過去20期間のEMA。短期トレンドを示す。")
        st.info("💡 押し目買い・戻り売りのタイミングを図るのに使われます。")
    
    with st.expander("**EMA 200（長期）**", expanded=False):
        st.plotly_chart(create_trend_diagram("uptrend"), use_container_width=True)
        st.write("過去200期間のEMA。長期トレンドを示す最重要ライン。")
        st.info("💡 価格がEMA200より上か下かでトレンドの方向を判断します。")
    
    with st.expander("**RSI（相対力指数）**", expanded=False):
        st.plotly_chart(create_rsi_diagram(), use_container_width=True)
        st.write("一定期間の値上がり幅と値下がり幅から、買われすぎ・売られすぎを判断する指標。0〜100の値をとる。")
        st.markdown("""
        | RSI値 | 状態 | 判断 |
        |-------|------|------|
        | 70以上 | 買われすぎ | 売りを検討 |
        | 30以下 | 売られすぎ | 買いを検討 |
        | 40-60 | 中立 | 様子見 |
        """)
        st.info("💡 トレンド方向と組み合わせて使うと効果的です。")
    
    with st.expander("**押し目**", expanded=False):
        st.plotly_chart(create_trend_diagram("pullback"), use_container_width=True)
        st.write("上昇トレンド中に一時的に価格が下がること。黄色のゾーンが押し目。")
        st.info("💡 押し目で買うのがトレンドフォローの基本戦略です！")
    
    with st.expander("**戻り**", expanded=False):
        st.plotly_chart(create_trend_diagram("rally"), use_container_width=True)
        st.write("下落トレンド中に一時的に価格が上がること。黄色のゾーンが戻り。")
        st.info("💡 戻りで売るのがトレンドフォローの基本戦略です！")


def render_chart_patterns():
    """チャートパターンの用語"""
    
    st.subheader("📈 チャートパターン")
    
    with st.expander("**ピンバー（下ヒゲ・買いシグナル）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("pin_bar_bullish"), use_container_width=True)
        st.write("長い下ヒゲと短い実体を持つローソク足。下落が止まり上昇に転じるサイン。")
        st.info("💡 下落トレンドの底で出現すると信頼度が高い！")
    
    with st.expander("**ピンバー（上ヒゲ・売りシグナル）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("pin_bar_bearish"), use_container_width=True)
        st.write("長い上ヒゲと短い実体を持つローソク足。上昇が止まり下落に転じるサイン。")
        st.info("💡 上昇トレンドの天井で出現すると信頼度が高い！")
    
    with st.expander("**陽線包み足（買いシグナル）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("engulfing_bullish"), use_container_width=True)
        st.write("前の陰線を完全に包み込む大きな陽線。強い買いシグナル。")
        st.info("💡 「前日の売りを今日の買いが飲み込んだ」イメージです。")
    
    with st.expander("**陰線包み足（売りシグナル）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("engulfing_bearish"), use_container_width=True)
        st.write("前の陽線を完全に包み込む大きな陰線。強い売りシグナル。")
        st.info("💡 「前日の買いを今日の売りが飲み込んだ」イメージです。")
    
    with st.expander("**十字線（同事線）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("doji"), use_container_width=True)
        st.write("始値と終値がほぼ同じで、実体がほとんどないローソク足。")
        st.info("💡 相場の迷いを示し、トレンド転換の可能性を示唆します。")
    
    with st.expander("**はらみ線**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("harami"), use_container_width=True)
        st.write("前のローソク足の実体の中に収まる小さなローソク足。")
        st.info("💡 トレンド転換の兆候ですが、包み足ほど強いシグナルではありません。")
    
    with st.expander("**三川明けの明星（強い買いシグナル）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("morning_star"), use_container_width=True)
        st.write("下落後に現れる3本のパターン。陰線→小さい足→陽線。")
        st.markdown("1. 大きな陰線（下落継続）\n2. 小さな足（迷い）\n3. 大きな陽線（反転上昇）")
        st.info("💡 強い上昇転換シグナル！底打ちのサインです。")
    
    with st.expander("**三川宵の明星（強い売りシグナル）**", expanded=False):
        st.plotly_chart(create_candlestick_diagram("evening_star"), use_container_width=True)
        st.write("上昇後に現れる3本のパターン。陽線→小さい足→陰線。")
        st.markdown("1. 大きな陽線（上昇継続）\n2. 小さな足（迷い）\n3. 大きな陰線（反転下落）")
        st.info("💡 強い下落転換シグナル！天井のサインです。")


def render_signal_terms():
    """シグナル関連用語"""
    
    st.subheader("🚦 シグナル用語")
    
    with st.expander("**環境認識**", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_trend_diagram("uptrend"), use_container_width=True)
        with col2:
            st.plotly_chart(create_trend_diagram("downtrend"), use_container_width=True)
        st.write("トレードを行う前に、相場全体のトレンドや状況を把握すること。")
        st.markdown("""
        **確認ポイント:**
        - 上位足（4時間足）のトレンドは？
        - メイン足（15分足）のトレンドは？
        - 価格はEMA200より上？下？
        """)
        st.info("💡 両方の時間足が同じ方向なら信頼度UP！")
    
    with st.expander("**セットアップ**", expanded=False):
        st.plotly_chart(create_trend_diagram("pullback"), use_container_width=True)
        st.write("エントリーの準備が整った状態。条件が揃ってトリガーを待つ段階。")
        st.markdown("""
        **買いセットアップの例:**
        - ✅ 上昇トレンド確認済み
        - ✅ 価格がEMA20付近まで下落
        - ✅ RSIが40以下
        - ⏳ トリガー待ち...
        """)
        st.info("💡 セットアップが整っただけではまだエントリーしない！")
    
    with st.expander("**トリガー**", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_candlestick_diagram("pin_bar_bullish"), use_container_width=True)
        with col2:
            st.plotly_chart(create_candlestick_diagram("engulfing_bullish"), use_container_width=True)
        st.write("実際にエントリーするきっかけとなるシグナル。")
        st.markdown("""
        **買いトリガーの例:**
        - ピンバー（下ヒゲ）が出現
        - 陽線の包み足が出現
        """)
        st.info("💡 セットアップ + トリガー = エントリー！")
    
    with st.expander("**シグナル判定の流れ**", expanded=False):
        st.markdown("""
        ```
        ┌─────────────────────────┐
        │  ① 環境認識（トレンド）  │
        │    終値 vs EMA200        │
        └───────────┬─────────────┘
                    ▼
        ┌─────────────────────────┐
        │  ② セットアップ（条件）  │
        │    20EMA付近？RSI条件？   │
        └───────────┬─────────────┘
                    ▼
        ┌─────────────────────────┐
        │  ③ トリガー（パターン）  │
        │    ピンバー？包み足？     │
        └───────────┬─────────────┘
                    ▼
              🎯 シグナル発生！
        ```
        """)
        st.info("💡 3つの条件が揃って初めてエントリー！")
    
    with st.expander("**ダマシ**", expanded=False):
        st.markdown("""
        シグナルが出たにもかかわらず、期待と逆方向に動くこと。
        
        **ダマシを減らすコツ:**
        - 上位足のトレンドに逆らわない
        - 複数の条件が揃った時だけエントリー
        - 必ず損切りを設定する
        """)
        st.warning("⚠️ どんなシグナルも100%ではありません。リスク管理が重要！")


def render_trade_terms():
    """トレード関連用語"""
    
    st.subheader("💹 トレード用語")
    
    with st.expander("**リスクリワード比率**", expanded=False):
        st.plotly_chart(create_risk_reward_diagram(), use_container_width=True)
        st.write("想定される損失（リスク）と利益（リワード）の比率。")
        st.markdown("""
        **リスクリワード 1:2 の場合:**
        - リスク（損失）: 5円
        - リワード（利益）: 10円
        - → 2回に1回勝てばトントン！
        - → 3回に2回勝てば利益！
        """)
        st.info("💡 1:2以上を目指すのが一般的。")
    
    with st.expander("**エントリー**", expanded=False):
        st.markdown("""
        ポジションを持つこと。買いまたは売りの注文を出すこと。
        
        **良いエントリーのポイント:**
        - 環境認識 ✅
        - セットアップ ✅
        - トリガー ✅
        - 損切りライン決定済み ✅
        """)
        st.info("💡 準備なしのエントリーはギャンブルです！")
    
    with st.expander("**損切り（ストップロス）**", expanded=False):
        st.plotly_chart(create_risk_reward_diagram(), use_container_width=True)
        st.write("損失を限定するために、あらかじめ決めた価格で決済すること。")
        st.markdown("""
        **損切りの設定例:**
        - 買いの場合: 直近安値の少し下
        - 売りの場合: 直近高値の少し上
        """)
        st.warning("⚠️ 損切りを設定しないトレードは絶対NG！")
    
    with st.expander("**利確（利益確定）**", expanded=False):
        st.write("利益が出ている状態で決済して利益を確定すること。")
        st.markdown("""
        **利確の設定例:**
        - リスクリワード1:2で計算
        - 次の抵抗線・支持線の手前
        """)
        st.info("💡 欲張りすぎると利益が減ることも。計画的に！")
    
    with st.expander("**トレードスタイル**", expanded=False):
        st.markdown("""
        | スタイル | 保有期間 | 使う時間足 |
        |----------|----------|------------|
        | スキャルピング | 数秒〜数分 | 1分足、5分足 |
        | デイトレード | 数分〜数時間 | 15分足、1時間足 |
        | スイングトレード | 数日〜数週間 | 4時間足、日足 |
        """)
        st.info("💡 このアプリは15分足を使ったデイトレード向けです。")
    
    with st.expander("**🏆 ランク判定システム**", expanded=False):
        st.markdown("""
        このアプリでは、銘柄の総合評価を **S/A/B/C ランク** で表示しています。
        
        ### 📊 テクニカル評価（100点満点）
        
        | 評価項目 | 条件 | 点数 |
        |----------|------|:----:|
        | **トレンド** | Price > 200EMA | +20点 |
        | | 20EMA > 200EMA | +20点 |
        | **モメンタム** | RSI 30〜40（押し目ゾーン） | +30点 |
        | | RSI < 30（売られすぎ） | +25点 |
        | | RSI 40〜60（中立） | +20点 |
        | | RSI > 70（買われすぎ） | 0点 |
        | **出来高** | デフォルト | +10点 |
        
        ### 💰 価格ボーナス（最大10点）
        少額投資家向けの優遇ポイント
        
        | 株価 | ボーナス |
        |------|:--------:|
        | 1,000円未満 | **+10点** |
        | 1,000〜3,000円 | **+5点** |
        | 3,000円以上 | 0点 |
        
        ### 🎯 AI分析時の総合スコア
        ```
        総合スコア = (テクニカル × 70%) + (AI感情 × 30%) + 価格ボーナス
        ```
        
        ### 🏅 ランク基準
        
        | ランク | スコア | 意味 |
        |:------:|:------:|------|
        | 🏆 **S** | 80点以上 | 最優良（買い推奨度：高） |
        | 🥇 **A** | 60〜79点 | 優良（検討価値あり） |
        | 🥈 **B** | 40〜59点 | 普通（慎重に検討） |
        | 🥉 **C** | 40点未満 | 低評価（見送り推奨） |
        """)
        st.success("💡 Sランク銘柄を中心に、A/Bランクも候補として検討しましょう！")
        st.warning("⚠️ ランクはあくまで参考値です。最終判断はご自身で！")


def render_glossary_sidebar():
    """サイドバー用のミニ用語解説"""
    with st.expander("📚 用語クイックリファレンス"):
        st.markdown("""
        **よく使う用語**
        - **EMA 200**: 長期トレンド判断
        - **EMA 20**: 押し目の目安
        - **RSI < 30**: 売られすぎ
        - **RSI > 70**: 買われすぎ
        """)
