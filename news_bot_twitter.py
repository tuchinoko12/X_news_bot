import os
import requests
import feedparser
import google.generativeai as genai
import json
import tweepy
from dotenv import load_dotenv

# ================= 設定 =================
load_dotenv()

API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URL = "https://www3.nhk.or.jp/rss/news/cat0.xml"
HISTORY_FILE = "sent_news.json"

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# X クライアント
# ==========================================
def get_twitter_client():
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    return client

# ==========================================
# トレンド取得
# ==========================================
def get_trend_words(limit=5):
    """日本と世界のトレンドから上位ワードを数件取得"""
    try:
        api = tweepy.API(
            tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        )
        trends_japan = api.get_place_trends(23424856)[0]["trends"]
        trends_world = api.get_place_trends(1)[0]["trends"]

        words = [t["name"] for t in (trends_japan + trends_world)[:limit]]
        return words
    except:
        return []

# ==========================================
# 履歴（変更なし）
# ==========================================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(url):
    history = load_history()
    history = list(set(history))
    if url not in history:
        history.append(url)
    history = history[-50:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ==========================================
# RSS
# ==========================================
def fetch_latest_news(limit=10):
    try:
        feed = feedparser.parse(RSS_URL)
        return [{"title": e.title, "summary": e.summary, "url": e.link} for e in feed.entries[:limit]]
    except:
        return []

# ==========================================
# Gemini（★ここを大幅改修）
# ==========================================
def process_news_with_gemini(news_list, trend_words):
    news_data = [{"title": n["title"], "url": n["url"]} for n in news_list]

    prompt = f"""
以下のニュース一覧から重要な1件を選び、以下のJSON形式だけ返してください。

・ハッシュタグは絶対に使わない。
・文章は150〜200文字以内。
・皮肉とツッコミを入れたJK口調。
・文頭は【速報】、【悲報】、【朗報】のいずれかを状況に応じて使う。
・トレンドワードを文章に自然に混ぜること（無理やりはNG）。
・人の目を引く工夫として、適度に絵文字を入れる。
・バズりやすい構造（共感 → ツッコミ → 軽いオチ）。

トレンドワード: {trend_words}

形式:
{{
    "selected_url": "ニュースURL",
    "text": "Xに投稿する本文（150〜200文字）"
}}

ニュース一覧:
{json.dumps(news_data, ensure_ascii=False)}
"""

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    raw = response.text.strip()

    try:
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        return json.loads(raw[json_start:json_end])
    except Exception as e:
        print("JSONパース失敗:", raw)
        raise e

# ==========================================
# 投稿
# ==========================================
def post_to_twitter(message):
    try:
        client = get_twitter_client()
        response = client.create_tweet(text=message)
        print(f"✅ X投稿成功！ ID: {response.data['id']}")
        return True

    except tweepy.TweepyException as e:
        print(f"❌ X投稿失敗: {e}")
        return False

# ==========================================
# メイン
# ==========================================
if __name__ == "__main__":
    try:
        history = load_history()
        latest_news = fetch_latest_news()

        news_list_unseen = [n for n in latest_news if n["url"] not in history]
        if not news_list_unseen:
            print("新しいニュースなし")
            exit()

        trend_words = get_trend_words(limit=5)
        result = process_news_with_gemini(news_list_unseen, trend_words)

        text = result.get("text", "")
        url = result.get("selected_url", "")

        # 投稿
        tweet_text = f"{text}\n{url}"

        if post_to_twitter(tweet_text):
            save_history(url)

    except Exception as e:
        print(f"Error: {e}")
