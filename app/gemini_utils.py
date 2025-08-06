import os
import io
import asyncio
from itertools import cycle
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# =============================
# 🔑 Load Environment Variables
# =============================
load_dotenv()

keys = os.getenv("GEMINI_KEYS", "").split(",")
keys = [k.strip() for k in keys if k.strip()]

if not keys:
    raise ValueError("❌ No Gemini API keys found. Please set GEMINI_KEYS in .env")

key_pool = cycle(keys)

# =============================
# 📌 Helper: Convert PIL Image -> Gemini Blob
# =============================
def _convert_image_to_blob(image):
    """Converts a PIL Image to a Gemini-compatible Blob format."""
    if image is None:
        return None
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return {"mime_type": "image/png", "data": buffer.read()}
    except Exception as e:
        print("⚠️ Image conversion failed:", e)
        return None

# =============================
# 🌟 Internal Gemini Call Helpers
# =============================
async def _call_gemini_content(prompt, image=None):
    """Calls Gemini API for multimodal (image + text) or text-only prompts."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    try:
        if image is not None:
            blob = _convert_image_to_blob(image)
            if blob:
                response = await model.generate_content_async([prompt, blob])
            else:
                response = await model.generate_content_async(prompt)
        else:
            response = await model.generate_content_async(prompt)

        return getattr(response, "text", str(response)).strip()

    except Exception as e:
        print("❌ Gemini content call failed:", e)
        raise

async def _call_gemini_text(prompt):
    """Calls Gemini API for text-only prompts."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    try:
        response = await model.generate_content_async(prompt)
        return getattr(response, "text", str(response)).strip()
    except Exception as e:
        print("❌ Gemini text call failed:", e)
        raise

# =============================
# 🚀 Public API Functions
# =============================
async def generate_content_async(prompt, image=None, retries=None):
    """
    Handles Gemini multimodal requests with:
    - Automatic API key rotation
    - Retry logic for quota/rate errors
    - 40s timeout protection
    """
    if retries is None:
        retries = len(keys)

    delay = 0.5
    for _ in range(retries):
        key = next(key_pool)
        genai.configure(api_key=key)
        try:
            return await asyncio.wait_for(_call_gemini_content(prompt, image), timeout=40)
        except asyncio.TimeoutError:
            print(f"⏳ Gemini content request timeout with key {key[:6]}... Retrying...")
        except Exception as e:
            err = str(e).lower()
            print(f"⚠️ Gemini content key failed ({key[:6]}...): {err}")
            if "quota" in err or "429" in err or "rate" in err:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 6)
                continue
            raise

    return "❌ All Gemini keys exhausted or content request failed."

async def generate_text_async(prompt, retries=None):
    """
    Handles Gemini text-only requests with:
    - Automatic API key rotation
    - Retry logic for quota/rate errors
    - 40s timeout protection
    """
    if retries is None:
        retries = len(keys)

    delay = 0.5
    for _ in range(retries):
        key = next(key_pool)
        genai.configure(api_key=key)
        try:
            return await asyncio.wait_for(_call_gemini_text(prompt), timeout=40)
        except asyncio.TimeoutError:
            print(f"⏳ Gemini text request timeout with key {key[:6]}... Retrying...")
        except Exception as e:
            err = str(e).lower()
            print(f"⚠️ Gemini text key failed ({key[:6]}...): {err}")
            if "quota" in err or "429" in err or "rate" in err:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 6)
                continue
            raise

    return "❌ All Gemini keys exhausted or text request failed."
