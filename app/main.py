import os
import io
import time
import base64
import logging
import requests
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError

# === Import Prompts & Utils ===
from app.prompts import (
    EDITING_PROMPTS,
    get_caption_prompt,
    get_caption_validator_prompt,
    get_music_prompt,
    MOOD_SCENE_PROMPT,
    get_chat_prompt,
    get_style_and_app_prompt
)
from app.gemini_utils import generate_content_async, generate_text_async

# =============================
# 🚀 FastAPI App Initialization
# =============================
app = FastAPI(title="Glamo - AI Photo Editing Assistant")

# ✅ Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ✅ Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"➡️ {request.method} {request.url}")
    response = await call_next(request)
    logging.info(f"⬅️ {request.method} {request.url} - {response.status_code}")
    return response

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Detect paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# ✅ Mount static files
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    logging.info(f"✅ Static directory mounted: {STATIC_DIR}")
else:
    logging.warning(f"⚠️ Static folder not found -> {STATIC_DIR}")

# ✅ Template engine
if os.path.isdir(TEMPLATES_DIR):
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
else:
    raise RuntimeError(f"❌ [ERROR] Templates folder not found -> {TEMPLATES_DIR}")

# =============================
# 🎵 Spotify Auth & Music Fetch
# =============================
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "YOUR_SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "YOUR_SPOTIFY_CLIENT_SECRET")
SPOTIFY_TOKEN = None
SPOTIFY_TOKEN_EXPIRY = 0


def get_spotify_token():
    """Fetch or refresh Spotify API token."""
    global SPOTIFY_TOKEN, SPOTIFY_TOKEN_EXPIRY

    if SPOTIFY_TOKEN and time.time() < SPOTIFY_TOKEN_EXPIRY:
        return SPOTIFY_TOKEN

    try:
        auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()

        res = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {b64_auth}"},
            data={"grant_type": "client_credentials"}
        )

        if res.status_code != 200:
            logging.warning(f"⚠️ Spotify Authentication Failed: {res.text}")
            return None

        data = res.json()
        SPOTIFY_TOKEN = data.get("access_token")
        SPOTIFY_TOKEN_EXPIRY = time.time() + data.get("expires_in", 3600)
        return SPOTIFY_TOKEN

    except Exception as e:
        logging.error(f"❌ Spotify token error: {e}")
        return None


def search_spotify_song(query):
    """Search for a song on Spotify."""
    token = get_spotify_token()
    if not token:
        return None

    try:
        url = "https://api.spotify.com/v1/search"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "type": "track", "limit": 1}

        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            tracks = res.json().get("tracks", {}).get("items", [])
            if tracks:
                track = tracks[0]
                return {
                    "title": track["name"],
                    "artist": ", ".join(a["name"] for a in track["artists"]),
                    "image": track["album"]["images"][0]["url"] if track["album"]["images"] else "/static/music-default.jpg",
                    "preview": track.get("preview_url")
                }
        else:
            logging.warning(f"⚠️ Spotify Search Failed: {query} | {res.status_code} | {res.text}")
    except Exception as e:
        logging.error(f"❌ Spotify search error: {e}")

    return None


def search_jiosaavn_song(query):
    """Search for a song on JioSaavn."""
    try:
        res = requests.get(f"https://saavn.dev/api/search/songs?query={query}")
        if res.status_code == 200:
            data = res.json()
            if "data" in data and data["data"].get("results"):
                song = data["data"]["results"][0]
                return {
                    "title": song.get("title"),
                    "artist": song.get("primaryArtists"),
                    "image": song["image"][-1]["link"] if song.get("image") else "/static/music-default.jpg",
                    "link": song.get("url")
                }
    except Exception as e:
        logging.warning(f"⚠️ JioSaavn Search Failed: {query} | {e}")

    return None

# =============================
# 📌 Utility: Downscale image
# =============================
def downscale_image(image: Image.Image, max_size=512):
    """Downscale the image proportionally."""
    try:
        image.thumbnail((max_size, max_size))
        return image
    except Exception as e:
        logging.warning(f"⚠️ Image downscaling failed: {e}")
        return image

# =============================
# 🏠 Home Page
# =============================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logging.error(f"❌ Template error: {e}")
        return HTMLResponse("<h2>Template not found or error rendering page.</h2>", status_code=500)

# =============================
# 🧠 Analyze Image
# =============================
@app.post("/analyze")
async def analyze_image(photo: UploadFile = File(...), selected_app: str = Form(...), style: str = Form(...)):
    try:
        image_bytes = await photo.read()
        if not image_bytes:
            return JSONResponse({"error": "No image uploaded."}, status_code=400)

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            return JSONResponse({"error": "Invalid image file."}, status_code=400)

        image = downscale_image(image)

        # --- Mood, Scene, Colors ---
        try:
            mood_data = await generate_content_async(MOOD_SCENE_PROMPT, image=image)
            mood, scene, colors = "Unknown", "Unknown", "Unknown"
            for line in mood_data.splitlines():
                if line.lower().startswith("mood:"):
                    mood = line.split(":", 1)[1].strip()
                elif line.lower().startswith("scene:"):
                    scene = line.split(":", 1)[1].strip()
                elif line.lower().startswith("colors:"):
                    colors = line.split(":", 1)[1].strip()
        except Exception as e:
            logging.error(f"❌ Mood detection failed: {e}")
            mood_data = "Mood: Unknown\nScene: Unknown\nColors: Unknown"
            mood, scene, colors = "Unknown", "Unknown", "Unknown"

        # --- Editing Suggestions ---
        try:
            editing_prompt = EDITING_PROMPTS.get(selected_app.lower())
            editing_text = await generate_content_async(editing_prompt(style), image=image) if editing_prompt \
                else "Step 1: Auto Enhance – Apply\nReason: Default enhancement."
        except Exception as e:
            logging.error(f"❌ Editing generation failed: {e}")
            editing_text = "Step 1: Auto Enhance – Apply\nReason: Default enhancement."

        # --- Captions ---
        try:
            caption_prompt = get_caption_prompt(style, mood, scene, colors)
            raw_captions = await generate_content_async(caption_prompt, image=image)
            validator_prompt = get_caption_validator_prompt(style, mood, scene, raw_captions)
            validator_result = await generate_text_async(validator_prompt)

            captions = [line.strip() for line in raw_captions.splitlines() if line.strip()][:5] \
                if "valid" in validator_result.lower() else \
                ["#Glamo #GlowGoals #Inspo", "#VibeCheck #Glamo #Magic"]
        except Exception as e:
            logging.error(f"❌ Caption generation failed: {e}")
            captions = ["#Glamo #GlowGoals #Inspo", "#VibeCheck #Glamo #Magic"]

        # --- Music Suggestions ---
        songs = []
        try:
            music_prompt = get_music_prompt(mood, scene, colors)
            music_response = await generate_content_async(music_prompt, image=image)
            titles = [line.split("🎵 ")[1].strip() for line in music_response.splitlines() if line.startswith("🎵 ")]
            for title in titles:
                song = search_spotify_song(title) or search_jiosaavn_song(title)
                if song:
                    songs.append(song)

            if len(songs) < 2:
                songs = [
                    {"title": "Lakshya", "artist": "Shankar Ehsaan Loy", "image": "/static/music-default.jpg"},
                    {"title": "Zinda", "artist": "Siddharth Mahadevan", "image": "/static/music-default.jpg"}
                ]
        except Exception as e:
            logging.error(f"❌ Music fetch failed: {e}")
            songs = [
                {"title": "Lakshya", "artist": "Shankar Ehsaan Loy", "image": "/static/music-default.jpg"},
                {"title": "Zinda", "artist": "Siddharth Mahadevan", "image": "/static/music-default.jpg"}
            ]

        return JSONResponse({
            "editing_values": editing_text,
            "captions": captions,
            "songs": songs,
            "mood_info": mood_data
        })

    except Exception as e:
        logging.error(f"❌ General analyze error: {e}")
        return JSONResponse({
            "editing_values": "Something went wrong.",
            "captions": [],
            "songs": [],
            "mood_info": ""
        }, status_code=500)

# =============================
# 💬 Chat Assistant
# =============================
@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        question = data.get("question", "")
        if not question:
            return {"answer": "Please enter a question."}
        prompt = get_chat_prompt(question)
        response = await generate_text_async(prompt)
        return {"answer": response.strip()}
    except Exception as e:
        logging.error(f"❌ Chat error: {e}")
        return {"answer": "Oops! Something went wrong."}

# =============================
# 🔮 Suggest Best Style & App
# =============================
@app.post("/suggest_style_app")
async def suggest_style_app(photo: UploadFile = File(...)):
    try:
        image_bytes = await photo.read()
        if not image_bytes:
            return {"result": "No image uploaded."}

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            return {"result": "Invalid image file."}

        image = downscale_image(image)
        prompt = get_style_and_app_prompt()
        response = await generate_content_async(prompt, image=image)
        return {"result": response.strip()}

    except Exception as e:
        logging.error(f"❌ Suggest Style/App failed: {e}")
        return {"result": "Style: Bright & Airy\nApp: iPhone Photos App\nReason: Default fallback."}










# from flask import Flask, request, jsonify, render_template
# from flask_cors import CORS
# import os
# import io
# from PIL import Image
# from dotenv import load_dotenv
# import google.generativeai as genai

# # === Load Prompts ===
# from prompts import (
#     EDITING_PROMPTS,
#     get_caption_prompt,
#     get_caption_validator_prompt,
#     get_music_prompt,
#     MOOD_SCENE_PROMPT,
#     get_chat_prompt,
#     get_style_and_app_prompt
# )

# # === Load Music Metadata Logic ===
# from music_metadata import (
#     get_song_data,
#     get_fallback_music,
#     filter_music_output
# )

# # === Setup ===
# load_dotenv()
# gemini_api_key = os.getenv("GEMINI_API_KEY")

# print("Gemini API Key:", gemini_api_key[:8] + "..." if gemini_api_key else "Not Found!")

# app = Flask(__name__)
# CORS(app)
# app.config['UPLOAD_FOLDER'] = 'uploads'
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# genai.configure(api_key=gemini_api_key)
# model = genai.GenerativeModel("gemini-1.5-flash")

# # === Home ===
# @app.route('/')
# def home():
#     return render_template("index.html")

# # === Analyze Image ===
# @app.route('/analyze', methods=['POST'])
# def analyze_image():
#     try:
#         photo = request.files['photo']
#         app_choice = request.form['app'].strip().lower()
#         style_choice = request.form['style'].strip()
#         image_bytes = photo.read()
#         image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

#         # === Mood, Scene, Colors ===
#         try:
#             mood_response = model.generate_content([MOOD_SCENE_PROMPT, image])
#             mood_data = mood_response.text.strip()
#             print("🧠 Mood Info:\n", mood_data)

#             mood = scene = colors = "Unknown"
#             for line in mood_data.splitlines():
#                 if line.lower().startswith("mood:"):
#                     mood = line.split(":", 1)[1].strip()
#                 elif line.lower().startswith("scene:"):
#                     scene = line.split(":", 1)[1].strip()
#                 elif line.lower().startswith("colors:"):
#                     colors = line.split(":", 1)[1].strip()
#         except Exception as e:
#             print("❌ Mood Detection Failed:", str(e))
#             mood_data = "Mood: Unknown\nScene: Unknown\nColors: Unknown"
#             mood = scene = colors = "Unknown"

#         # === Editing Steps ===
#         try:
#             editing_prompt = EDITING_PROMPTS[app_choice](style_choice)
#             editing_response = model.generate_content([editing_prompt, image])
#             editing_text = editing_response.text.strip()
#         except Exception as e:
#             print("❌ Editing Generation Failed:", str(e))
#             editing_text = "Step 1: Auto Enhance – Apply\nReason: Basic enhancement."

#         # === Captions ===
#         try:
#             caption_prompt = get_caption_prompt(style_choice, mood, scene, colors)
#             caption_response = model.generate_content([caption_prompt, image])
#             raw_captions = caption_response.text.strip()

#             validator_prompt = get_caption_validator_prompt(style_choice, mood, scene, raw_captions)
#             validator_response = model.generate_content(validator_prompt)

#             if "valid" in validator_response.text.lower():
#                 captions = [line.strip() for line in raw_captions.splitlines() if line.strip()][:5]
#             else:
#                 raise ValueError("❌ Captions didn't pass validation.")
#         except Exception as e:
#             print("❌ Caption Generation Failed:", str(e))
#             captions = ["#Glamo #GlowGoals #Inspo", "#VibeCheck #Glamo #Magic"]

#         # === Music Suggestions ===
#         try:
#             music_prompt = get_music_prompt(mood, scene, colors)
#             music_response = model.generate_content([music_prompt, image])
#             raw_music = music_response.text.strip()

#             print("🎶 Raw Music Suggestions:\n", raw_music)

#             titles = [line.split("🎵 ")[1].strip() for line in raw_music.splitlines() if line.startswith("🎵 ")]
#             songs = [get_song_data(title) for title in titles if title]

#             # Fallback if not enough songs
#             if len(songs) < 5:
#                 print("⚠️ Less than 5 songs. Using fallback.")
#                 songs = get_fallback_music(mood)

#             # Set fallback image if missing
#             for song in songs:
#                 if not song.get("image"):
#                     song["image"] = "/static/default_cover.png"
#         except Exception as e:
#             print("❌ Music Fetch Failed:", str(e))
#             songs = get_fallback_music("romantic")
#             for song in songs:
#                 if not song.get("image"):
#                     song["image"] = "/static/default_cover.png"

#         return jsonify({
#             'editing_values': editing_text,
#             'captions': captions,
#             'songs': songs,
#             'mood_info': mood_data
#         })

#     except Exception as e:
#         print("❌ General Error:", str(e))
#         return jsonify({
#             'editing_values': 'Something went wrong.',
#             'captions': [],
#             'songs': [],
#             'mood_info': ''
#         })

# # === Chat Assistant ===
# @app.route("/chat", methods=["POST"])
# def chat_with_glamo():
#     try:
#         question = request.json.get("question", "")
#         if not question:
#             return jsonify({"answer": "Please enter a question."})

#         prompt = get_chat_prompt(question)
#         response = model.generate_content(prompt)
#         return jsonify({"answer": response.text.strip()})
#     except Exception as e:
#         print("❌ Chat Error:", str(e))
#         return jsonify({"answer": "Oops! Something went wrong."})

# # === Suggest Style + App ===
# @app.route('/suggest_style_app', methods=['POST'])
# def suggest_style_app():
#     try:
#         file = request.files['photo']
#         image = Image.open(io.BytesIO(file.read())).convert("RGB")
#         prompt = get_style_and_app_prompt()
#         response = model.generate_content([prompt, image])
#         result = response.text.strip()
#         print("🧠 Style & App Suggestion:", result)
#         return jsonify({'result': result})
#     except Exception as e:
#         print("❌ Suggest Style/App Failed:", str(e))
#         return jsonify({'result': 'Style: Bright & Airy\nApp: iPhone Photos App\nReason: Default fallback.'})

# # === Run Server ===
# if __name__ == '__main__':
#     app.run(debug=True)

