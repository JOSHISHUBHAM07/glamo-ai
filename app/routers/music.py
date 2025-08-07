import os
import time
import base64
import logging
import requests
from fastapi import APIRouter, HTTPException

# Create a new router object. This is like a "mini" FastAPI app.
router = APIRouter(
    prefix="/music",  # All routes in this file will start with /music
    tags=["Music"],     # This groups the routes in the API docs
)

# =============================
# 🎵 Spotify Auth & Music Fetch
# =============================
# All music-related code now lives in this file.
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_TOKEN = None
SPOTIFY_TOKEN_EXPIRY = 0


def get_spotify_token():
    """Fetch or refresh Spotify API token."""
    global SPOTIFY_TOKEN, SPOTIFY_TOKEN_EXPIRY

    if SPOTIFY_TOKEN and time.time() < SPOTIFY_TOKEN_EXPIRY:
        return SPOTIFY_TOKEN

    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        logging.error("❌ Spotify credentials are not set in environment variables.")
        return None

    try:
        auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()

        res = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {b64_auth}"},
            data={"grant_type": "client_credentials"}
        )

        res.raise_for_status()  # This will raise an error for bad responses (4xx or 5xx)

        data = res.json()
        SPOTIFY_TOKEN = data.get("access_token")
        SPOTIFY_TOKEN_EXPIRY = time.time() + data.get("expires_in", 3600)
        return SPOTIFY_TOKEN

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Spotify Authentication Failed: {e}")
        return None
    except Exception as e:
        logging.error(f"❌ An unexpected error occurred during Spotify token fetch: {e}")
        return None


def search_spotify_song(query: str):
    """Search for a song on Spotify."""
    token = get_spotify_token()
    if not token:
        return None

    try:
        url = "https://api.spotify.com/v1/search"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "type": "track", "limit": 1}

        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        
        tracks = res.json().get("tracks", {}).get("items", [])
        if tracks:
            track = tracks[0]
            return {
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "image": track["album"]["images"][0]["url"] if track["album"]["images"] else "/static/music-default.jpg",
                "preview": track.get("preview_url")
            }
    except requests.exceptions.RequestException as e:
        logging.warning(f"⚠️ Spotify Search Failed: {query} | {e}")
    except Exception as e:
        logging.error(f"❌ An unexpected error occurred during Spotify search: {e}")

    return None


def search_jiosaavn_song(query: str):
    """Search for a song on JioSaavn."""
    try:
        res = requests.get(f"https://saavn.dev/api/search/songs?query={query}")
        res.raise_for_status()
        
        data = res.json()
        if "data" in data and data["data"].get("results"):
            song = data["data"]["results"][0]
            return {
                "title": song.get("name"), # Corrected from "title" to "name" for consistency
                "artist": song.get("primaryArtists"),
                "image": song["image"][-1]["link"] if song.get("image") else "/static/music-default.jpg",
                "link": song.get("url")
            }
    except requests.exceptions.RequestException as e:
        logging.warning(f"⚠️ JioSaavn Search Failed: {query} | {e}")
    except Exception as e:
        logging.error(f"❌ An unexpected error occurred during JioSaavn search: {e}")

    return None
