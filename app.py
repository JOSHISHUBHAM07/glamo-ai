from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import io
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

# === Load Prompts ===
from prompts import (
    EDITING_PROMPTS,
    get_caption_prompt,
    get_caption_validator_prompt,
    get_music_prompt,
    MOOD_SCENE_PROMPT,
    get_chat_prompt,
    get_style_and_app_prompt
)

# === Load Music Metadata Logic ===
from music_metadata import (
    get_song_data,
    get_fallback_music,
    filter_music_output
)

# === Setup ===
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

print("Gemini API Key:", gemini_api_key[:8] + "..." if gemini_api_key else "Not Found!")

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# === Home ===
@app.route('/')
def home():
    return render_template("index.html")

# === Analyze Image ===
@app.route('/analyze', methods=['POST'])
def analyze_image():
    try:
        photo = request.files['photo']
        app_choice = request.form['app'].strip().lower()
        style_choice = request.form['style'].strip()
        image_bytes = photo.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # === Mood, Scene, Colors ===
        try:
            mood_response = model.generate_content([MOOD_SCENE_PROMPT, image])
            mood_data = mood_response.text.strip()
            print("🧠 Mood Info:\n", mood_data)

            mood = scene = colors = "Unknown"
            for line in mood_data.splitlines():
                if line.lower().startswith("mood:"):
                    mood = line.split(":", 1)[1].strip()
                elif line.lower().startswith("scene:"):
                    scene = line.split(":", 1)[1].strip()
                elif line.lower().startswith("colors:"):
                    colors = line.split(":", 1)[1].strip()
        except Exception as e:
            print("❌ Mood Detection Failed:", str(e))
            mood_data = "Mood: Unknown\nScene: Unknown\nColors: Unknown"
            mood = scene = colors = "Unknown"

        # === Editing Steps ===
        try:
            editing_prompt = EDITING_PROMPTS[app_choice](style_choice)
            editing_response = model.generate_content([editing_prompt, image])
            editing_text = editing_response.text.strip()
        except Exception as e:
            print("❌ Editing Generation Failed:", str(e))
            editing_text = "Step 1: Auto Enhance – Apply\nReason: Basic enhancement."

        # === Captions ===
        try:
            caption_prompt = get_caption_prompt(style_choice, mood, scene, colors)
            caption_response = model.generate_content([caption_prompt, image])
            raw_captions = caption_response.text.strip()

            validator_prompt = get_caption_validator_prompt(style_choice, mood, scene, raw_captions)
            validator_response = model.generate_content(validator_prompt)

            if "valid" in validator_response.text.lower():
                captions = [line.strip() for line in raw_captions.splitlines() if line.strip()][:5]
            else:
                raise ValueError("❌ Captions didn't pass validation.")
        except Exception as e:
            print("❌ Caption Generation Failed:", str(e))
            captions = ["#Glamo #GlowGoals #Inspo", "#VibeCheck #Glamo #Magic"]

        # === Music Suggestions ===
        try:
            music_prompt = get_music_prompt(mood, scene, colors)
            music_response = model.generate_content([music_prompt, image])
            raw_music = music_response.text.strip()

            print("🎶 Raw Music Suggestions:\n", raw_music)

            titles = [line.split("🎵 ")[1].strip() for line in raw_music.splitlines() if line.startswith("🎵 ")]
            songs = [get_song_data(title) for title in titles if title]

            # Fallback if not enough songs
            if len(songs) < 5:
                print("⚠️ Less than 5 songs. Using fallback.")
                songs = get_fallback_music(mood)

            # Set fallback image if missing
            for song in songs:
                if not song.get("image"):
                    song["image"] = "/static/default_cover.png"
        except Exception as e:
            print("❌ Music Fetch Failed:", str(e))
            songs = get_fallback_music("romantic")
            for song in songs:
                if not song.get("image"):
                    song["image"] = "/static/default_cover.png"

        return jsonify({
            'editing_values': editing_text,
            'captions': captions,
            'songs': songs,
            'mood_info': mood_data
        })

    except Exception as e:
        print("❌ General Error:", str(e))
        return jsonify({
            'editing_values': 'Something went wrong.',
            'captions': [],
            'songs': [],
            'mood_info': ''
        })

# === Chat Assistant ===
@app.route("/chat", methods=["POST"])
def chat_with_glamo():
    try:
        question = request.json.get("question", "")
        if not question:
            return jsonify({"answer": "Please enter a question."})

        prompt = get_chat_prompt(question)
        response = model.generate_content(prompt)
        return jsonify({"answer": response.text.strip()})
    except Exception as e:
        print("❌ Chat Error:", str(e))
        return jsonify({"answer": "Oops! Something went wrong."})

# === Suggest Style + App ===
@app.route('/suggest_style_app', methods=['POST'])
def suggest_style_app():
    try:
        file = request.files['photo']
        image = Image.open(io.BytesIO(file.read())).convert("RGB")
        prompt = get_style_and_app_prompt()
        response = model.generate_content([prompt, image])
        result = response.text.strip()
        print("🧠 Style & App Suggestion:", result)
        return jsonify({'result': result})
    except Exception as e:
        print("❌ Suggest Style/App Failed:", str(e))
        return jsonify({'result': 'Style: Bright & Airy\nApp: iPhone Photos App\nReason: Default fallback.'})

# === Run Server ===
if __name__ == '__main__':
    app.run(debug=True)





#good start
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
#     get_music_prompt,
#     MOOD_SCENE_PROMPT,
#     get_chat_prompt,
#     get_style_and_app_prompt
# )

# # === Setup ===
# load_dotenv()
# gemini_api_key = os.getenv("GEMINI_API_KEY")
# print("🔑 Gemini API Key:", gemini_api_key[:8] + "..." if gemini_api_key else "Not Found!")

# genai.configure(api_key=gemini_api_key)
# model = genai.GenerativeModel("gemini-1.5-flash")

# app = Flask(__name__)
# CORS(app)
# app.config['UPLOAD_FOLDER'] = 'uploads'
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# # === Music Filtering (Phase 3 & 6) ===
# def filter_music_output(raw_text):
#     lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
#     cleaned = []
#     count = 0
#     for i in range(len(lines)):
#         if lines[i].startswith("🎵"):
#             try:
#                 if lines[i + 1].startswith("🎯") or lines[i + 1].startswith("🌟"):
#                     cleaned.append(lines[i])
#                     cleaned.append(lines[i + 1])
#                     count += 1
#             except IndexError:
#                 continue
#         if count == 6:
#             break
#     return "\n".join(cleaned) if count == 6 else ""

# # === Music Fallback (Phase 4) ===
# MUSIC_LIBRARY = {
#     "romantic": {
#         "hindi": ["Raabta", "Tum Mile", "Pee Loon"],
#         "english": ["Perfect", "Until I Found You", "All of Me"]
#     },
#     "dreamy": {
#         "hindi": ["Agar Tum Saath Ho", "Phir Le Aaya Dil", "Jiyein Kyun"],
#         "english": ["Sunflower", "Golden Hour", "Lost in Japan"]
#     },
#     "bold": {
#         "hindi": ["Malang", "Apna Time Aayega", "Zinda"],
#         "english": ["Believer", "Unstoppable", "God Is A Woman"]
#     }
# }

# def get_fallback_music(mood):
#     mood = mood.lower()
#     data = MUSIC_LIBRARY.get(mood, MUSIC_LIBRARY["romantic"])
#     songs = ""
#     for title in data["hindi"]:
#         songs += f"🎵 {title}\n🎯 Reason: Matches the {mood} Hindi vibe\n\n"
#     for title in data["english"]:
#         songs += f"🎵 {title}\n🎯 Reason: Captures the {mood} English tone\n\n"
#     return songs.strip()

# # === Home Route ===
# @app.route('/')
# def home():
#     return render_template("index.html")

# # === Analyze Image Route ===
# @app.route('/analyze', methods=['POST'])
# def analyze_image():
#     try:
#         photo = request.files['photo']
#         app_choice = request.form['app'].strip().lower()
#         style_choice = request.form['style'].strip()
#         image_bytes = photo.read()
#         image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

#         # === 1. Editing Steps ===
#         editing_prompt_func = EDITING_PROMPTS.get(app_choice)
#         if not editing_prompt_func:
#             raise ValueError(f"No prompt found for app: {app_choice}")
#         editing_prompt = editing_prompt_func(style_choice)

#         try:
#             editing_response = model.generate_content([editing_prompt, image])
#             editing_text = editing_response.text.strip()
#             print("✅ Editing Steps:\n", editing_text)
#         except Exception as e:
#             print("❌ Editing Generation Failed:", str(e))
#             editing_text = "Step 1: Auto Enhance – Apply\nReason: Basic enhancement."

#         # === 2. Captions ===
#         caption_prompt = get_caption_prompt(style_choice)
#         try:
#             caption_response = model.generate_content([caption_prompt, image])
#             raw = caption_response.text.strip()
#             captions = [
#                 line.strip("-\u2022* ").strip()
#                 for line in raw.split("\n")
#                 if line.strip() and not any(x in line.lower() for x in ["caption", "example"])
#             ][:5]
#             if len(captions) < 3:
#                 raise ValueError("Too few valid captions")
#         except Exception as e:
#             print("❌ Captions Failed:", str(e))
#             captions = [
#                 "#Glamo #GlowGoals", "#VibeCheck #Glamo", "#MoodInFrame #Glamo",
#                 "#ChicClick #Glamo", "#StyleSnaps #Glamo"
#             ]

#         # === 3. Mood & Scene Detection ===
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

#         # === 4. Music ===
#         try:
#             music_prompt = get_music_prompt(mood, scene, colors)
#             music_response = model.generate_content([music_prompt, image])
#             raw_music = music_response.text.strip()
#             songs = filter_music_output(raw_music)

#             if not songs or len(songs.split("🎵")) < 7:
#                 songs = get_fallback_music(mood)

#             print("🎶 Songs:\n", songs)
#         except Exception as e:
#             print("❌ Music Failed:", str(e))
#             songs = get_fallback_music("romantic")

#         # === Return Results ===
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
#             'songs': '',
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

# # === AI Suggests Best Style & App ===
# @app.route('/suggest_style_app', methods=['POST'])
# def suggest_style_app():
#     try:
#         file = request.files['photo']
#         image = Image.open(io.BytesIO(file.read())).convert("RGB")
#         prompt = get_style_and_app_prompt()

#         response = model.generate_content([prompt, image])
#         result = response.text.strip()
#         print("🔮 Style & App Suggestion:", result)
#         return jsonify({'result': result})

#     except Exception as e:
#         print("❌ Error in suggest_style_app:", str(e))
#         return jsonify({'result': 'Style: Bright & Airy\nApp: iPhone Photos App\nReason: Default fallback.'})

# # === Run App ===
# if __name__ == '__main__':
#     app.run(debug=True)


#good end







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
#     get_music_prompt,
#     MOOD_SCENE_PROMPT,
#     get_chat_prompt,
#     get_style_and_app_prompt
# )

# # === Setup ===
# load_dotenv()
# gemini_api_key = os.getenv("GEMINI_API_KEY")
# print("🔑 Gemini API Key:", gemini_api_key[:8] + "..." if gemini_api_key else "Not Found!")

# genai.configure(api_key=gemini_api_key)
# model = genai.GenerativeModel("gemini-1.5-flash")

# app = Flask(__name__)
# CORS(app)
# app.config['UPLOAD_FOLDER'] = 'uploads'
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# # === Music Filtering (Phase 3) ===
# def filter_music_output(raw_text):
#     lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
#     cleaned = []
#     count = 0
#     for i in range(len(lines)):
#         if lines[i].startswith("🎵"):
#             try:
#                 if lines[i + 1].startswith("🎯"):
#                     cleaned.append(lines[i])
#                     cleaned.append(lines[i + 1])
#                     count += 1
#             except IndexError:
#                 continue
#         if count == 6:
#             break
#     return "\n".join(cleaned) if count == 6 else ""

# # === Music Fallback (Phase 4) ===
# MUSIC_LIBRARY = {
#     "romantic": {
#         "hindi": ["Raabta", "Tum Mile", "Pee Loon"],
#         "english": ["Perfect", "Until I Found You", "All of Me"]
#     },
#     "dreamy": {
#         "hindi": ["Agar Tum Saath Ho", "Phir Le Aaya Dil", "Jiyein Kyun"],
#         "english": ["Sunflower", "Golden Hour", "Lost in Japan"]
#     },
#     "bold": {
#         "hindi": ["Malang", "Apna Time Aayega", "Zinda"],
#         "english": ["Believer", "Unstoppable", "God Is A Woman"]
#     }
# }

# def get_fallback_music(mood):
#     mood = mood.lower()
#     data = MUSIC_LIBRARY.get(mood, MUSIC_LIBRARY["romantic"])
#     songs = ""
#     for title in data["hindi"]:
#         songs += f"🎵 {title}\n🎯 Reason: Matches the {mood} Hindi vibe\n\n"
#     for title in data["english"]:
#         songs += f"🎵 {title}\n🎯 Reason: Captures the {mood} English tone\n\n"
#     return songs.strip()

# # === Home Route ===
# @app.route('/')
# def home():
#     return render_template("index.html")

# # === Analyze Image Route ===
# @app.route('/analyze', methods=['POST'])
# def analyze_image():
#     try:
#         photo = request.files['photo']
#         app_choice = request.form['app'].strip().lower()
#         style_choice = request.form['style'].strip()
#         image_bytes = photo.read()
#         image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

#         # === 1. Editing Steps ===
#         editing_prompt_func = EDITING_PROMPTS.get(app_choice)
#         if not editing_prompt_func:
#             raise ValueError(f"No prompt found for app: {app_choice}")
#         editing_prompt = editing_prompt_func(style_choice)

#         try:
#             editing_response = model.generate_content([editing_prompt, image])
#             editing_text = editing_response.text.strip()
#             print("✅ Editing Steps:\n", editing_text)
#         except Exception as e:
#             print("❌ Editing Generation Failed:", str(e))
#             editing_text = "Step 1: Auto Enhance – Apply\nReason: Basic enhancement."

#         # === 2. Captions ===
#         caption_prompt = get_caption_prompt(style_choice)
#         try:
#             caption_response = model.generate_content([caption_prompt, image])
#             raw = caption_response.text.strip()
#             captions = [
#                 line.strip("-\u2022* ").strip()
#                 for line in raw.split("\n")
#                 if line.strip() and not any(x in line.lower() for x in ["caption", "example"])
#             ][:5]
#             if len(captions) < 3:
#                 raise ValueError("Too few valid captions")
#         except Exception as e:
#             print("❌ Captions Failed:", str(e))
#             captions = [
#                 "#Glamo #GlowGoals", "#VibeCheck #Glamo", "#MoodInFrame #Glamo",
#                 "#ChicClick #Glamo", "#StyleSnaps #Glamo"
#             ]

#         # === 3. Mood & Scene Detection ===
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

#         # === 4. Music ===
#         try:
#             music_prompt = get_music_prompt(mood, scene, colors)
#             music_response = model.generate_content([music_prompt, image])
#             raw_music = music_response.text.strip()
#             songs = filter_music_output(raw_music)

#             if not songs or len(songs.split("🎵")) < 7:
#                 songs = get_fallback_music(mood)

#             print("🎶 Songs:\n", songs)
#         except Exception as e:
#             print("❌ Music Failed:", str(e))
#             songs = get_fallback_music("romantic")

#         # === Return Results ===
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
#             'songs': '',
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

# # === AI Suggests Best Style & App ===
# @app.route('/suggest_style_app', methods=['POST'])
# def suggest_style_app():
#     try:
#         file = request.files['photo']
#         image = Image.open(io.BytesIO(file.read())).convert("RGB")
#         prompt = get_style_and_app_prompt()

#         response = model.generate_content([prompt, image])
#         result = response.text.strip()
#         print("🔮 Style & App Suggestion:", result)
#         return jsonify({'result': result})

#     except Exception as e:
#         print("❌ Error in suggest_style_app:", str(e))
#         return jsonify({'result': 'Style: Bright & Airy\nApp: iPhone Photos App\nReason: Default fallback.'})

# # === Run App ===
# if __name__ == '__main__':
#     app.run(debug=True)










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
#     get_music_prompt,  # UPDATED: Dynamic music prompt
#     MOOD_SCENE_PROMPT,
#     get_chat_prompt,
#     get_style_and_app_prompt
# )

# # === Setup ===
# load_dotenv()
# gemini_api_key = os.getenv("GEMINI_API_KEY")
# print("🔑 Gemini API Key:", gemini_api_key[:8] + "..." if gemini_api_key else "Not Found!")

# genai.configure(api_key=gemini_api_key)
# model = genai.GenerativeModel("gemini-1.5-flash")

# app = Flask(__name__)
# CORS(app)
# app.config['UPLOAD_FOLDER'] = 'uploads'
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# # === Home Route ===
# @app.route('/')
# def home():
#     return render_template("index.html")

# # === Analyze Image Route ===
# @app.route('/analyze', methods=['POST'])
# def analyze_image():
#     try:
#         photo = request.files['photo']
#         app_choice = request.form['app'].strip().lower()
#         style_choice = request.form['style'].strip()
#         image_bytes = photo.read()
#         image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

#         # === 1. Editing Steps ===
#         editing_prompt_func = EDITING_PROMPTS.get(app_choice)
#         if not editing_prompt_func:
#             raise ValueError(f"No prompt found for app: {app_choice}")
#         editing_prompt = editing_prompt_func(style_choice)

#         try:
#             editing_response = model.generate_content([editing_prompt, image])
#             editing_text = editing_response.text.strip()
#             print("✅ Editing Steps:\n", editing_text)
#         except Exception as e:
#             print("❌ Editing Generation Failed:", str(e))
#             editing_text = "Step 1: Auto Enhance – Apply\nReason: Basic enhancement."

#         # === 2. Captions ===
#         caption_prompt = get_caption_prompt(style_choice)
#         try:
#             caption_response = model.generate_content([caption_prompt, image])
#             raw = caption_response.text.strip()
#             captions = [
#                 line.strip("-\u2022* ").strip()
#                 for line in raw.split("\n")
#                 if line.strip() and not any(x in line.lower() for x in ["caption", "example"])
#             ][:5]
#             if len(captions) < 3:
#                 raise ValueError("Too few valid captions")
#         except Exception as e:
#             print("❌ Captions Failed:", str(e))
#             captions = [
#                 "#Glamo #GlowGoals", "#VibeCheck #Glamo", "#MoodInFrame #Glamo",
#                 "#ChicClick #Glamo", "#StyleSnaps #Glamo"
#             ]

#         # === 3. Mood & Scene Detection ===
#         try:
#             mood_response = model.generate_content([MOOD_SCENE_PROMPT, image])
#             mood_data = mood_response.text.strip()
#             print("🧠 Mood Info:\n", mood_data)

#             # Extract values for dynamic music prompt
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

#         # === 4. Music ===
#         try:
#             music_prompt = get_music_prompt(mood, scene, colors)
#             music_response = model.generate_content([music_prompt, image])
#             songs = music_response.text.strip()
#             print("🎶 Songs:\n", songs)
#         except Exception as e:
#             print("❌ Music Failed:", str(e))
#             songs = (
#                 "🎵 Golden Hour\n🌟 Reason: Fits dreamy golden tones\n\n"
#                 "🎵 Ocean Eyes\n🌟 Reason: Complements soft emotional portraits\n\n"
#                 "🎵 Raabta\n🌟 Reason: Romantic and moody tones"
#             )

#         # === Return Results ===
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
#             'songs': '',
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

# # === AI Suggests Best Style & App ===
# @app.route('/suggest_style_app', methods=['POST'])
# def suggest_style_app():
#     try:
#         file = request.files['photo']
#         image = Image.open(io.BytesIO(file.read())).convert("RGB")
#         prompt = get_style_and_app_prompt()

#         response = model.generate_content([prompt, image])
#         result = response.text.strip()
#         print("🔮 Style & App Suggestion:", result)
#         return jsonify({'result': result})

#     except Exception as e:
#         print("❌ Error in suggest_style_app:", str(e))
#         return jsonify({'result': 'Style: Bright & Airy\nApp: iPhone Photos App\nReason: Default fallback.'})

# # === Run App ===
# if __name__ == '__main__':
#     app.run(debug=True)
