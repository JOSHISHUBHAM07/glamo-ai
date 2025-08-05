import os
import requests
from dotenv import load_dotenv

load_dotenv()

# === Credentials ===
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# === Spotify Token ===
def get_spotify_token():
    url = "https://accounts.spotify.com/api/token"
    auth = (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}

    try:
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print("❌ Spotify Token Error:", e)
        return None

# === Spotify Search ===
def search_spotify(song_title, token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": song_title, "type": "track", "limit": 1}
        response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
        response.raise_for_status()
        items = response.json().get("tracks", {}).get("items", [])
        if items:
            track = items[0]
            return {
                "title": track["name"],
                "artist": track["artists"][0]["name"],
                "album": track["album"]["name"],
                "image": track["album"]["images"][0]["url"],
                "preview_url": track["preview_url"],
                "source": "Spotify"
            }
    except Exception as e:
        print(f"⚠️ Spotify Search Failed: {song_title} |", e)
    return None

# === JioSaavn Search ===
def search_jiosaavn(song_title):
    try:
        url = f"https://saavn.dev/api/search/songs?query={song_title}"
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get("data", {}).get("results", [])
        if results:
            song = results[0]
            return {
                "title": song["title"],
                "artist": song["primaryArtists"],
                "album": song["album"]["name"],
                "image": song["image"],
                "preview_url": song["downloadUrl"][-1]["link"] if song.get("downloadUrl") else None,
                "source": "JioSaavn"
            }
    except Exception as e:
        print(f"⚠️ JioSaavn Search Failed: {song_title} |", e)
    return None

# === Smart Metadata Resolver ===
def get_song_data(song_title):
    song_title = song_title.strip()
    if not song_title:
        return None

    # Hindi keyword detection
    hindi_keywords = ["tere", "mera", "dil", "saath", "tum", "pyar", "yaar", "ke", "ki", "hai", "mein"]
    is_hindi = any(word.lower() in song_title.lower() for word in hindi_keywords)

    if is_hindi:
        jio_result = search_jiosaavn(song_title)
        if jio_result:
            return jio_result

    token = get_spotify_token()
    if token:
        spotify_result = search_spotify(song_title, token)
        if spotify_result:
            return spotify_result

    return {
        "title": song_title,
        "artist": "Unknown",
        "album": "N/A",
        "image": None,
        "preview_url": None,
        "source": "AI"
    }

# === Fallback Music Library ===
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
        "english": ["Believer", "Unstoppable", "God Is A Woman"]
    }
}

# === Fallback Music Generator ===
def get_fallback_music(mood):
    mood = mood.lower()
    songs = MUSIC_LIBRARY.get(mood, MUSIC_LIBRARY["romantic"])
    titles = songs["hindi"] + songs["english"]

    results = []
    for title in titles:
        song = get_song_data(title)
        if song:
            results.append(song)
    return results

# === Clean + Deduplicate Music Results ===
def filter_music_output(songs):
    seen = set()
    filtered = []
    for song in songs:
        key = (song["title"].lower(), song["artist"].lower())
        if key not in seen:
            seen.add(key)
            filtered.append(song)
    return filtered
