import os
import time
import base64
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === Credentials ===
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# === Cache ===
_spotify_cache = {"token": None, "expiry": 0}

# ==============================
# 🎵 Spotify Token Generator
# ==============================
def get_spotify_token():
    """
    Retrieves a fresh Spotify API token using Client Credentials Flow.
    Uses in-memory cache with expiry to avoid repeated requests.
    """
    global _spotify_cache

    # Return cached token if valid
    if _spotify_cache["token"] and time.time() < _spotify_cache["expiry"]:
        return _spotify_cache["token"]

    try:
        auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()

        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {b64_auth}"},
            data={"grant_type": "client_credentials"},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        token = data.get("access_token")
        expiry = time.time() + data.get("expires_in", 3600)

        _spotify_cache.update({"token": token, "expiry": expiry})
        return token
    except Exception as e:
        print("❌ Spotify Token Error:", e)
        return None


# ==============================
# 🎵 Spotify Search
# ==============================
def search_spotify(song_title):
    """
    Searches Spotify API for the given song title and returns metadata.
    """
    token = get_spotify_token()
    if not token:
        return None

    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": song_title, "type": "track", "limit": 1}
        response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params, timeout=10)
        response.raise_for_status()

        items = response.json().get("tracks", {}).get("items", [])
        if items:
            track = items[0]
            return {
                "title": track.get("name", song_title),
                "artist": ", ".join(a["name"] for a in track.get("artists", [])) or "Unknown",
                "album": track.get("album", {}).get("name", "N/A"),
                "image": track.get("album", {}).get("images", [{}])[0].get("url", "/static/music-default.jpg"),
                "preview": track.get("preview_url"),
                "language": "english",
                "source": "Spotify"
            }
    except Exception as e:
        print(f"⚠️ Spotify Search Failed: {song_title} |", e)
    return None


# ==============================
# 🎵 JioSaavn Search
# ==============================
def search_jiosaavn(song_title):
    """
    Searches JioSaavn unofficial API for Hindi music results and returns metadata.
    """
    try:
        url = f"https://saavn.dev/api/search/songs?query={song_title}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        results = response.json().get("data", {}).get("results", [])
        if results:
            song = results[0]
            image_url = song.get("image")
            if isinstance(image_url, list):
                image_url = image_url[-1].get("link", "/static/music-default.jpg")

            return {
                "title": song.get("title", song_title),
                "artist": song.get("primaryArtists", "Unknown"),
                "album": song.get("album", {}).get("name", "N/A"),
                "image": image_url or "/static/music-default.jpg",
                "preview": song["downloadUrl"][-1]["link"] if song.get("downloadUrl") else None,
                "language": "hindi",
                "source": "JioSaavn"
            }
    except Exception as e:
        print(f"⚠️ JioSaavn Search Failed: {song_title} |", e)
    return None


# ==============================
# 🎵 Smart Metadata Resolver
# ==============================
def get_song_data(song_title):
    """
    Attempts to fetch a song's metadata from JioSaavn (Hindi) or Spotify (English).
    Falls back to a basic object if APIs fail.
    """
    song_title = song_title.strip()
    if not song_title:
        return None

    # Detect Hindi based on keywords
    hindi_keywords = ["tere", "mera", "dil", "saath", "tum", "pyar", "yaar", "ke", "ki", "hai", "mein", "hoon", "chal"]
    is_hindi = any(word in song_title.lower() for word in hindi_keywords)

    # 1️⃣ Try JioSaavn for Hindi
    if is_hindi:
        jio_result = search_jiosaavn(song_title)
        if jio_result:
            return jio_result

    # 2️⃣ Try Spotify
    spotify_result = search_spotify(song_title)
    if spotify_result:
        return spotify_result

    # 3️⃣ Default fallback
    return {
        "title": song_title,
        "artist": "Unknown",
        "album": "N/A",
        "image": "/static/music-default.jpg",
        "preview": None,
        "language": "hindi" if is_hindi else "english",
        "source": "AI-Fallback"
    }


# ==============================
# 🎵 Fallback Music Library
# ==============================
MUSIC_LIBRARY = {
    "romantic": {
        "hindi": ["Raabta", "Tum Mile", "Pee Loon"],
        "english": ["Perfect", "Until I Found You", "All of Me"]
    },
    "dreamy": {
        "hindi": ["Agar Tum Saath Ho", "Phir Le Aaya Dil", "Jiyein Kyun"],
        "english": ["Sunflower", "Golden Hour", "Lost in Japan"]
    },
    "bold": {
        "hindi": ["Malang", "Apna Time Aayega", "Zinda"],
        "english": ["Believer", "Unstoppable", "Eye of the Tiger"]
    }
}


# ==============================
# 🎵 Fallback Music Generator
# ==============================
def get_fallback_music(mood):
    """
    Returns a set of fallback music recommendations when both APIs fail.
    """
    mood = mood.lower()
    songs = MUSIC_LIBRARY.get(mood, MUSIC_LIBRARY["romantic"])
    titles = songs["hindi"] + songs["english"]

    results = []
    for title in titles:
        song = get_song_data(title)
        if song:
            results.append(song)

    return filter_music_output(results)


# ==============================
# 🎵 Deduplicate Music Output
# ==============================
def filter_music_output(songs):
    """
    Removes duplicate songs by checking (title + artist) combination.
    """
    seen = set()
    filtered = []
    for song in songs:
        key = (song.get("title", "").lower(), (song.get("artist") or "unknown").lower())
        if key not in seen:
            seen.add(key)
            filtered.append(song)
    return filtered
