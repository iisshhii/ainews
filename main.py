import os
import feedparser
from google import genai
import time
import socket
import requests
from jinja2 import Template
from datetime import datetime
from dotenv import load_dotenv

# タイムアウト設定（ネットワーク系のハング防止）
socket.setdefaulttimeout(20)

print("--- Script Starting ---", flush=True)

# 環境変数の読み込み
load_dotenv()

# Gemini APIの設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    print(f"Gemini API Key found (Prefix: {GEMINI_API_KEY[:5]}...)", flush=True)
    client = genai.Client(api_key=GEMINI_API_KEY)
    # モデルIDを指定
    MODEL_ID = 'gemini-3.1-flash-lite-preview'
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.", flush=True)
    client = None

# RSSフィードのリスト（日本の金融・ビジネス系特化）
RSS_FEEDS = [
    {"name": "Yahoo!ニュース 経済", "url": "https://news.yahoo.co.jp/rss/topics/business.xml"},
    {"name": "東洋経済オンライン", "url": "https://toyokeizai.net/list/feed/rss"},
    {"name": "ITmedia ビジネス", "url": "https://rss.itmedia.co.jp/rss/2.0/business.xml"}
]

# ブラウザを装うためのヘッダー
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_news():
    print("Starting fetch_news()...", flush=True)
    news_items = []
    for feed in RSS_FEEDS:
        print(f"Fetching news from: {feed['name']} ({feed['url']})...", flush=True)
        try:
            # requestsを使用してタイムアウト付き・ヘッダー付きで取得
            response = requests.get(feed['url'], headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            # 取得したコンテンツをfeedparserで解析
            d = feedparser.parse(response.content)
            
            for entry in d.entries[:5]:  # 各フィードから最新5件を取得
                news_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "source": feed['name'],
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", "")
                })
            print(f"Successfully fetched {feed['name']}.", flush=True)
        except Exception as e:
            print(f"Error fetching {feed['name']}: {e}", flush=True)
            
    print(f"Fetched {len(news_items)} items total.", flush=True)
    return news_items

def summarize_news(news_items):
    print("Starting summarize_news()...", flush=True)
    summary_results = []
    if not client:
        print("Skipping summarization: Gemini API client not initialized.", flush=True)
        for item in news_items:
            item["ja_summary"] = "（APIキーが設定されていないため要約をスキップしました）"
            summary_results.append(item)
        return summary_results

    # 試行するモデルの優先順位リスト（確実に無料枠があるものに限定）
    FALLBACK_MODELS = [
        'gemini-3.1-flash-lite-preview',  # 本命（クォータ大）
        'gemini-2.5-flash',               # 予備1（無料枠5 RPMあり）
        'gemini-flash-latest',            # 予備2
    ]

    for item in news_items:
        print(f"Waiting 15s before summarizing: {item['title']}...", flush=True)
        time.sleep(15)  # レート制限回避（5 RPM = 1分間12秒間隔以上を確実にするため15秒）
        
        prompt = f"""
以下の日本語のニュース記事のタイトルと概要を読み、さらに分かりやすく3行以内で要約してください。
タイトル: {item['title']}
概要: {item['summary']}

形式:
- 簡潔に、重要なポイントのみを抽出
- 忙しいビジネスパーソンが内容をすぐに把握できるようにする
"""
        
        item["ja_summary"] = "要約の生成に失敗しました。"
        
        # モデルを順番に試す
        for model_id in FALLBACK_MODELS:
            try:
                print(f"Trying to summarize with {model_id}...", flush=True)
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt
                )
                item["ja_summary"] = response.text.strip()
                print(f"Successfully summarized with {model_id}: {item['title']}", flush=True)
                break # 成功したらループを抜ける
            except Exception as e:
                print(f"Error using {model_id}: {e}", flush=True)
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    print(f"{model_id} is busy, trying next model...", flush=True)
                    continue # 次のモデルへ
                else:
                    # それ以外のエラー（認証など）は致命的なので次のニュースへ
                    break
        
        summary_results.append(item)
    return summary_results

def generate_html(news_items):
    print("Generating HTML...", flush=True)
    template_str = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily AI News Curator</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Outfit:wght@300;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-color: #38bdf8;
            --accent-gradient: linear-gradient(135deg, #38bdf8, #818cf8);
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        header {
            text-align: center;
            margin-bottom: 60px;
            padding: 40px 0;
            background: rgba(30, 41, 59, 0.5);
            border-radius: 24px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        h1 {
            font-size: 3rem;
            margin: 0;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }

        .update-time {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 10px;
        }

        .news-grid {
            display: grid;
            gap: 24px;
        }

        .news-card {
            background-color: var(--card-bg);
            border-radius: 20px;
            padding: 30px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
            border: 1px solid rgba(255, 255, 255, 0.05);
            position: relative;
            overflow: hidden;
        }

        .news-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 186, 255, 0.1);
            border-color: var(--accent-color);
        }

        .news-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 4px; height: 100%;
            background: var(--accent-gradient);
        }

        .source-tag {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--accent-color);
            margin-bottom: 12px;
            font-weight: 600;
        }

        h2 {
            font-size: 1.4rem;
            margin: 0 0 15px 0;
            font-weight: 600;
        }

        h2 a {
            color: var(--text-primary);
            text-decoration: none;
        }

        .summary {
            font-family: 'Inter', sans-serif;
            color: var(--text-secondary);
            font-size: 1rem;
            margin-bottom: 20px;
        }

        .news-link {
            color: var(--accent-color);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
        }

        .news-link::after {
            content: '→';
            margin-left: 8px;
            transition: margin-left 0.2s;
        }

        .news-card:hover .news-link::after {
            margin-left: 12px;
        }

        footer {
            text-align: center;
            margin-top: 60px;
            color: var(--text-secondary);
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Daily AI News</h1>
            <div class="update-time">Last updated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}</div>
        </header>

        <div class="news-grid">
            {% for item in news %}
            <article class="news-card">
                <div class="source-tag">{{ item.source }}</div>
                <h2><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></h2>
                <div class="summary">
                    {{ item.ja_summary | replace('\\n', '<br>') | safe }}
                </div>
                <a href="{{ item.link }}" class="news-link" target="_blank">Read Original</a>
            </article>
            {% endfor %}
        </div>

        <footer>
            &copy; {{ now.year }} AI News Curator. Powered by Gemini.
        </footer>
    </div>
</body>
</html>
"""
    template = Template(template_str)
    html_content = template.render(news=news_items, now=datetime.now())
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("index.html generated successfully.", flush=True)

def main():
    news = fetch_news()
    summarized_news = summarize_news(news)
    generate_html(summarized_news)

if __name__ == "__main__":
    main()


