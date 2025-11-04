import os
import random
import base64
import requests
from io import BytesIO
from PIL import Image
from gradio_client import Client
import google.generativeai as genai

# ===== 環境変数 =====
API_KEY = os.getenv("API_KEY_1")
API_SECRET = os.getenv("API_SECRET_1")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN_1")
ACCESS_SECRET = os.getenv("ACCESS_SECRET_1")
BEARER_TOKEN = os.getenv("BEARER_TOKEN_1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_SPACE_ID = os.getenv("HF_SPACE_ID")  # 例: robotsan/X_bot_image

# ===== Gemini 初期化 =====
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash", api_version="v1")

# ===== ひらがな3文字生成 =====
def generate_word():
    hira = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
    return "".join(random.choice(hira) for _ in range(3))

# ===== 画像生成 =====
def generate_image(word):
    print("🎨 画像生成中...")
    prompt = f"『{word}』という日本語の単語から連想されるユーモラスでバズりそうなイラストや写真"

    try:
        client = Client(HF_SPACE_ID)
        result = client.predict(prompt, api_name="/predict")

        # Spaceが返すのが画像パス or base64 のどちらでも対応
        if isinstance(result, str) and result.endswith((".png", ".jpg", ".jpeg", ".webp")):
            image_url = result
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
        elif isinstance(result, list) and len(result) > 0:
            data = result[0]
            if data.startswith("data:image"):
                image_data = base64.b64decode(data.split(",")[1])
                image = Image.open(BytesIO(image_data))
            else:
                response = requests.get(data)
                image = Image.open(BytesIO(response.content))
        else:
            raise ValueError(f"画像生成APIの応答が不正です: {result}")

        file_name = f"{word}.png"
        image.save(file_name)
        return file_name
    except Exception as e:
        print(f"❌ 画像生成エラー: {e}")
        return None

# ===== ハッシュタグ生成 =====
def generate_hashtags(word):
    prompt = f"「{word}」に関連する日本語のユーモラスで自然なハッシュタグを10個生成してください。#をつけて改行で区切ってください。"
    try:
        response = model.generate_content(prompt)
        hashtags_text = response.text.strip()
        hashtags = [tag.strip() for tag in hashtags_text.split("\n") if tag.strip()]
        return hashtags[:10]
    except Exception as e:
        print(f"❌ ハッシュタグ生成エラー: {e}")
        return []

# ===== X（Twitter）に投稿 =====
def post_to_twitter(word, image_path):
    hashtags = generate_hashtags(word)
    tweet_text = f"生成単語: {word}\n" + " ".join(hashtags)

    try:
        # まずメディアをアップロード（旧v1.1 APIは無料で利用可能）
        media_id = None
        if image_path:
            upload_url = "https://upload.twitter.com/1.1/media/upload.json"
            files = {"media": open(image_path, "rb")}
            headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
            upload_resp = requests.post(upload_url, headers=headers, files=files)
            if upload_resp.status_code == 200:
                media_id = upload_resp.json().get("media_id_string")
            else:
                print(f"❌ メディアアップロード失敗: {upload_resp.text}")

        # 投稿（v2対応）
        post_url = "https://api.x.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"text": tweet_text}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}

        post_resp = requests.post(post_url, headers=headers, json=payload)
        if post_resp.status_code in (200, 201):
            print(f"✅ 投稿完了: {tweet_text}")
        else:
            print(f"❌ 投稿エラー: {post_resp.status_code} - {post_resp.text}")
    except Exception as e:
        print(f"❌ 投稿エラー: {e}")

# ===== メイン =====
def main():
    word = generate_word()
    print(f"🎲 生成単語: {word}")
    image_path = generate_image(word)
    post_to_twitter(word, image_path)

if __name__ == "__main__":
    main()
