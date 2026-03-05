import os
import feedparser
import google.generativeai as genai
from jinja2 import Template
from datetime import datetime
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Gemini APIの設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")
    model = None

# RSSフィードのリスト
RSS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"}
]

def fetch_news():
    news_items = []
    for feed in RSS_FEEDS:
        print(f"Fetching news from: {feed['name']}")
        d = feedparser.parse(feed['url'])
        for entry in d.entries[:5]:  # 各フィードから最新5件を取得
            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "source": feed['name'],
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")
            })
    return news_items

def summarize_news(news_items):
    summary_results = []
    if not model:
        print("Skipping summarization: Gemini API key not set.")
        for item in news_items:
            item["ja_summary"] = "（APIキーが設定されていないため要約をスキップしました）"
            summary_results.append(item)
        return summary_results

    for item in news_items:
        print(f"Summarizing: {item['title']}")
        prompt = f"""
以下の英語のニュース記事のタイトルと概要を読み、日本語で3行以内で要約してください。
タイトル: {item['title']}
概要: {item['summary']}

形式:
- 簡潔に、重要なポイントのみを抽出
- 読者が内容をすぐに把握できるようにする
"""
        try:
            response = model.generate_content(prompt)
            item["ja_summary"] = response.text.strip()
        except Exception as e:
            print(f"Error summarizing {item['title']}: {e}")
            item["ja_summary"] = "要約の生成に失敗しました。"
        
        summary_results.append(item)
    return summary_results

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI News Curator - 毎日更新</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Outfit:wght@300;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #030712;
            --card-bg: #111827;
            --text-main: #f9fafb;
            --text-dim: #9ca3af;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.3);
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }

        header {
            background: linear-gradient(135deg, #1e1b4b 0%, #030712 100%);
            padding: 4rem 2rem;
            text-align: center;
            border-bottom: 1px solid #1f2937;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 3.5rem;
            margin: 0;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .subtitle {
            font-size: 1.1rem;
            color: var(--text-dim);
            margin-top: 1rem;
        }

        .container {
            max-width: 1000px;
            margin: 3rem auto;
            padding: 0 1.5rem;
        }

        .news-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
            gap: 2rem;
        }

        @media (max-width: 600px) {
            .news-grid {
                grid-template-columns: 1fr;
            }
            h1 { font-size: 2.5rem; }
        }

        .card {
            background: var(--card-bg);
            border: 1px solid #1f2937;
            border-radius: 1.5rem;
            padding: 2rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .card:hover {
            transform: translateY(-5px);
            border-color: var(--accent);
            box-shadow: 0 10px 40px -10px var(--accent-glow);
        }

        .source-tag {
            font-size: 0.75rem;
            text-transform: uppercase;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 0.75rem;
            display: inline-block;
            letter-spacing: 0.05em;
        }

        .card h2 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.5rem;
            line-height: 1.3;
            margin: 0 0 1rem 0;
        }

        .summary {
            color: var(--text-dim);
            font-size: 1rem;
            margin-bottom: 1.5rem;
            white-space: pre-wrap;
        }

        .link-btn {
            display: inline-flex;
            align-items: center;
            color: var(--text-main);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: color 0.2s;
        }

        .link-btn:hover {
            color: var(--accent);
        }

        .link-btn::after {
            content: '→';
            margin-left: 0.5rem;
        }

        footer {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-dim);
            font-size: 0.875rem;
            border-top: 1px solid #1f2937;
        }

        .update-time {
            font-weight: 700;
            color: var(--text-main);
        }
    </style>
</head>
<body>
    <header>
        <h1>AI News Curator</h1>
        <p class="subtitle">最新のAIニュースをGeminiが要約。毎日自動更新。</p>
    </header>

    <div class="container">
        <div class="news-grid">
            {% for item in news %}
            <article class="card">
                <span class="source-tag">{{ item.source }}</span>
                <h2>{{ item.title }}</h2>
                <div class="summary">{{ item.ja_summary }}</div>
                <a href="{{ item.link }}" class="link-btn" target="_blank">ソースを読む</a>
            </article>
            {% endfor %}
        </div>
    </div>

    <footer>
        <p>最終更新: <span class="update-time">{{ update_time }}</span></p>
        <p>&copy; 2026 AI News Curator. All rights reserved.</p>
    </footer>
</body>
</html>
"""

def generate_html(news_items):
    template = Template(HTML_TEMPLATE)
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_content = template.render(news=news_items, update_time=update_time)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Successfully generated index.html")

def main():
    news = fetch_news()
    summarized_news = summarize_news(news)
    generate_html(summarized_news)

if __name__ == "__main__":
    main()


