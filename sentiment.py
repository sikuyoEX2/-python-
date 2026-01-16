"""
感情分析モジュール
Gemini APIを使用してニュースのポジティブ/ネガティブ判定を行う
"""
import streamlit as st
import yfinance as yf
from datetime import datetime, date
from typing import Tuple, Optional, List, Dict
import json
import os


# Gemini API設定
def get_gemini_model():
    """Gemini APIモデルを取得"""
    try:
        import google.generativeai as genai
        
        api_key = None
        
        # Streamlit secretsから取得
        try:
            if hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
                api_key = st.secrets['GEMINI_API_KEY']
        except:
            pass
        
        # 環境変数からフォールバック
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            return None
        
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-flash')
    except ImportError:
        print("google-generativeai not installed")
        return None
    except Exception as e:
        print(f"Gemini setup error: {e}")
        return None


class SentimentAnalyzer:
    """ニュース感情分析クラス"""
    
    def __init__(self):
        self.model = get_gemini_model()
        self._cache = {}  # メモリキャッシュ
    
    def is_available(self) -> bool:
        """Gemini APIが利用可能かどうか"""
        return self.model is not None
    
    def analyze_news(self, ticker: str, news_text: str) -> Tuple[int, str]:
        """
        ニューステキストを分析し、0-100のスコアを返す
        
        Args:
            ticker: 銘柄コード
            news_text: ニュース本文
        
        Returns:
            (スコア 0-100, 理由/要約)
        """
        if not self.model:
            return 50, "Gemini API未設定"
        
        prompt = f"""
あなたはプロの証券アナリストです。以下のニュースを読み、
対象銘柄({ticker})の株価にとってポジティブかネガティブかを判定してください。

出力ルール:
- 0(超悲観)〜100(超楽観)、50を中立とする整数スコア
- 短い理由（日本語で1-2文）

ニュース:
{news_text[:2000]}

出力フォーマット(JSON):
{{"score": 整数, "reason": "理由の文字列"}}
"""
        
        # リトライ処理（最大3回）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(text)
                score = int(data.get("score", 50))
                reason = data.get("reason", "分析完了")
                return max(0, min(100, score)), reason
            except json.JSONDecodeError:
                # JSONパースに失敗した場合、テキストから数値を抽出
                try:
                    import re
                    numbers = re.findall(r'\d+', response.text)
                    if numbers:
                        score = int(numbers[0])
                        return max(0, min(100, score)), "分析完了（部分解析）"
                except:
                    pass
                return 50, "解析エラー"
            except Exception as e:
                error_msg = str(e)
                # 429 (Rate Limit) エラーの場合はリトライ
                if "429" in error_msg or "quota" in error_msg.lower():
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(10)  # 10秒待機してリトライ
                        continue
                return 50, f"Error: {error_msg}"
        
        return 50, "リトライ上限到達"
    
    def get_news(self, ticker: str) -> List[Dict]:
        """
        yfinanceからニュースを取得
        
        Args:
            ticker: 銘柄コード
        
        Returns:
            ニュースのリスト
        """
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            if news:
                return news[:5]  # 最新5件
            return []
        except Exception as e:
            print(f"News fetch error: {e}")
            return []
    
    def get_sentiment(self, ticker: str) -> Tuple[int, str, List[Dict]]:
        """
        銘柄のニュース感情を分析
        
        Args:
            ticker: 銘柄コード
        
        Returns:
            (総合スコア, 要約, 個別ニュース分析結果)
        """
        # キャッシュ確認
        today = date.today().isoformat()
        cache_key = f"{ticker}_{today}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # ニュース取得
        news_list = self.get_news(ticker)
        
        if not news_list:
            result = (50, "ニュースが見つかりません", [])
            self._cache[cache_key] = result
            return result
        
        if not self.is_available():
            result = (50, "Gemini API未設定", [])
            self._cache[cache_key] = result
            return result
        
        # 各ニュースを分析
        results = []
        total_score = 0
        
        for news in news_list:
            title = news.get('title', '')
            summary = news.get('summary', title)
            
            score, reason = self.analyze_news(ticker, f"{title}\n{summary}")
            
            results.append({
                'title': title,
                'score': score,
                'reason': reason,
                'link': news.get('link', '')
            })
            total_score += score
        
        # 平均スコア
        avg_score = total_score // len(results) if results else 50
        
        # 要約
        if avg_score >= 70:
            summary = "📈 ポジティブなニュースが多い"
        elif avg_score <= 30:
            summary = "📉 ネガティブなニュースが多い"
        else:
            summary = "➡️ 中立的なニュース"
        
        result = (avg_score, summary, results)
        self._cache[cache_key] = result
        
        return result


def render_sentiment_panel(ticker: str):
    """
    感情分析パネルをStreamlitで表示
    """
    analyzer = SentimentAnalyzer()
    
    if not analyzer.is_available():
        st.warning("⚠️ Gemini APIキーが設定されていません。Secretsに`GEMINI_API_KEY`を追加してください。")
        return
    
    with st.spinner("🤖 ニュース感情分析中..."):
        score, summary, details = analyzer.get_sentiment(ticker)
    
    # スコア表示
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # スコアに応じた色
        if score >= 70:
            color = "🟢"
        elif score <= 30:
            color = "🔴"
        else:
            color = "🟡"
        
        st.metric(f"{color} AI感情スコア", f"{score}/100")
    
    with col2:
        st.write(f"**{summary}**")
        st.caption(f"分析対象: 最新{len(details)}件のニュース")
    
    # 詳細表示
    with st.expander("📰 個別ニュース分析"):
        for news in details:
            score_emoji = "🟢" if news['score'] >= 70 else "🔴" if news['score'] <= 30 else "🟡"
            st.markdown(f"**{score_emoji} {news['score']}点** - {news['title'][:60]}...")
            st.caption(news['reason'])
            if news.get('link'):
                st.markdown(f"[記事を読む]({news['link']})")
            st.divider()
