import os
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
# 履歴管理
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
    if url not in history:
        history.append(url)
    history = history[-50:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ==========================================
# NHK RSSニュース取得
# ==========================================
def fetch_latest_news(limit=10):
    try:
        feed = feedparser.parse(RSS_URL)
        return [{"title": e.title, "summary": e.summary, "url": e.link} for e in feed.entries[:limit]]
    except:
        return []


# ==========================================
# トレンドは API 使えないので Gemini に生成させる
# ==========================================
def generate_trend_words():
    prompt = """
Twitterのトレンドに出ていそうな日本語の単語を3〜5個生成してください。
形式は JSON で:
["ワード1", "ワード2", ...]
のみ返すこと。
"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    res = model.generate_content(prompt)

    raw = res.text.strip()
    json_start = raw.find("[")
    json_end = raw.rfind("]") + 1
    return json.loads(raw[json_start:json_end])


# ==========================================
# Gemini による投稿文生成（150〜200文字）
# ==========================================
def process_news_with_gemini(news_list, trend_words):
    news_data = [{"title": n["title"], "url": n["url"]} for n in news_list]

    prompt = f"""
以下のニュース一覧から重要な1件を選び、
150〜200文字でX投稿文を作成してください。

条件:
・文頭は【速報】【朗報】【悲報】のいずれか
・絵文字を適度に使う
・皮肉＋JK口調で軽めのツッコミ
・共感→ツッコミ→軽めのオチの流れ
・ハッシュタグ禁止
・以下のトレンドワードを自然に混ぜる（無理やりはNG）
→ {trend_words}

形式:
{{
  "selected_url": "ニュースURL",
  "text": "投稿文"
}}

ニュース:
{json.dumps(news_data, ensure_ascii=False)}
"""

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    raw = response.text.strip()

    json_start = raw.find("{")
    json_end = raw.rfind("}") + 1
    return json.loads(raw[json_start:json_end])


# ==========================================
# Xへ投稿（v2 API：Free Tierで最も成功率が高い）
# ==========================================
def post_to_twitter(message):
    try:
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )

        res = client.create_tweet(text=message)
        print("✅ X投稿成功:", res.data)
        return True

    except Exception as e:
        print("❌ X投稿失敗:", e)
        return False


# ==========================================
# メイン
# ==========================================
if __name__ == "__main__":
    try:
        history = load_history()
        latest_news = fetch_latest_news()
        trend_words = generate_trend_words()

        news_list_unseen = [n for n in latest_news if n["url"] not in history]
        if not news_list_unseen:
            print("新しいニュースなし")
            exit()

        result = process_news_with_gemini(news_list_unseen, trend_words)

        text = result.get("text", "")
        url = result.get("selected_url", "")

        tweet = f"{text}\n{url}"

        if post_to_twitter(tweet):
            save_history(url)

    except Exception as e:
        print("Error:", e)
