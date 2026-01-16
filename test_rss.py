
import urllib.request
import xml.etree.ElementTree as ET
import re

def get_google_news(ticker, limit=5):
    # 銘柄コードから検索クエリ作成 (例: "7203 トヨタ 株")
    # ここではシンプルにコードと"株"で検索
    query = f"{ticker} 株"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
    
    print(f"Fetching from: {url}")
    
    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        news_items = []
        
        # RSSのアイテムをパース
        for item in root.findall('.//item')[:limit]:
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else ""
            pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            # Google Newsのタイトルから発行元を取り除く処理（任意）
            # 例: "株価上昇の理由 - 日本経済新聞" -> "株価上昇の理由"
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1]
                
            news_items.append({
                'title': title,
                'link': link,
                'publisher': source,
                'published': pubDate
            })
            
        return news_items
        
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return []

# テスト
tickers = ["7203", "9984", "4502"]  # トヨタ, ソフトバンク, 武田薬品
for t in tickers:
    print(f"\n--- {t} ---")
    items = get_google_news(t)
    for i in items:
        print(f"[{i['publisher']}] {i['title']}")
