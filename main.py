import os
import random
import base64
import requests
from gradio_client import Client
import google.generativeai as genai
import tweepy

# === 設定 ===
# 環境変数（GitHub Secretsから読み込まれる）
API_KEY = os.getenv("API_KEY_1")
API_SECRET = os.getenv("API_SECRET_1")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN_1")
ACCESS_SECRET = os.getenv("ACCESS_SECRET_1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_SPACE_ID = os.getenv("HF_SPACE_ID")

# === Gemini設定 ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# === ランダム単語生成 ===
def generate_random_word():
    hiragana = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
    return ''.join(random.choices(hiragana, k=random.randint(3, 5)))

# === Hugging Faceで画像生成 ===
def generate_image(prompt):
    try:
        print("🎨 画像生成中...")
        client = client = Client(HF_SPACE_ID)
        result = client.predict(prompt, api_name="/predict")

        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], str):
            image_path = result[0]
            if image_path.startswith("/tmp"):
                raise ValueError(f"画像生成APIの応答が不正です: {image_path}")

            image_url = f"https://{HF_SPACE_ID}.hf.space/file={image_path}"
            response = requests.get(image_url)
            if response.status_code == 200:
                filename = "output.png"
                with open(filename, "wb") as f:
                    f.write(response.content)
                return filename
            else:
                raise ValueError(f"画像取得失敗: {response.status_code}")
        else:
            raise ValueError("画像生成APIの応答が不正です")
    except Exception as e:
        print(f"❌ 画像生成エラー: {e}")
        return None

# === Geminiでハッシュタグ生成 ===
def generate_hashtags(word):
    try:
        prompt = f"次の単語に合う日本語のハッシュタグを3つ生成してください。単語: {word}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ ハッシュタグ生成エラー: {e}")
        return ""

# === X（Twitter）に投稿 ===
import requests
import os

def post_to_twitter(text, image_path=None):
    try:
        BEARER_TOKEN = os.getenv("BEARER_TOKEN")  # XのBearerトークンを新しく.envに追加

        # まず画像をアップロードできるようにする（Freeではmedia不可のため、画像なしツイート推奨）
        if image_path and os.path.exists(image_path):
            print("⚠️ Freeプランでは画像付き投稿は非対応の可能性があります。")
        
        url = "https://api.x.com/2/tweets"
        headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
        payload = {"text": text}

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print("✅ 投稿完了！")
        else:
            print(f"❌ 投稿エラー: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 投稿エラー: {e}")

# === メイン処理 ===
if __name__ == "__main__":
    word = generate_random_word()
    print(f"🎲 生成単語: {word}")

    image_path = generate_image(word)
    hashtags = generate_hashtags(word)
    tweet_text = f"{word}\n{hashtags}"

    post_to_twitter(tweet_text, image_path)


