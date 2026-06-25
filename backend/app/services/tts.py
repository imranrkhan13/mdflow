"""
TTS fallback chain — 4 providers, all free, tried in order:

  1. edge-tts    — Microsoft neural voices. Best quality. No key, no quota.
                   Needs internet (speech.platform.bing.com).
                   Returns MP3.

  2. gTTS        — Google Translate TTS. Good quality. No key, no quota.
                   Needs internet (translate.google.com).
                   Returns MP3.

  3. pyttsx3     — Uses the OS's built-in speech engine.
                   macOS: uses built-in Siri/Alex voices.
                   Windows: uses SAPI5.
                   Fully offline, zero dependencies, zero network.
                   Returns WAV.

  4. Gemini TTS  — AI neural voices. Requires GEMINI_API_KEY. Has a free
                   tier quota. Used only as last resort if all above fail.
                   Returns WAV.

Why this order: quality first, then reliability. edge-tts and gTTS both
produce natural-sounding speech. pyttsx3 sounds more robotic but never
fails due to network or quotas. Gemini is held as last resort to avoid
burning quota unnecessarily.
"""
import asyncio
import base64
import io
import os
import struct
import tempfile

import httpx

from app.config import settings


class TTSError(Exception):
    pass


# ─── Voice definitions ───────────────────────────────────────────────────────

EDGE_VOICES = {
    "narrator": "en-US-AndrewNeural",
    "friendly": "en-US-AvaNeural",
    "calm":     "en-US-BrianNeural",
}

GTTS_TLDS = {
    # Different Google TLDs give subtly different accents
    "narrator": "com",
    "friendly": "co.uk",
    "calm":     "com.au",
}

PYTTSX3_RATES = {
    "narrator": 165,
    "friendly": 175,
    "calm":     150,
}

GEMINI_VOICES = {
    "narrator": "Charon",
    "friendly": "Puck",
    "calm":     "Kore",
}

VOICE_OPTIONS = list(EDGE_VOICES.keys())


# ─── WAV helper ──────────────────────────────────────────────────────────────

def _pcm_to_wav(pcm: bytes, rate=24000, channels=1, bits=16) -> bytes:
    byte_rate   = rate * channels * bits // 8
    block_align = channels * bits // 8
    size = len(pcm)
    hdr = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + size, b"WAVE",
        b"fmt ", 16, 1, channels, rate,
        byte_rate, block_align, bits,
        b"data", size,
    )
    return hdr + pcm


# ─── Provider 1: edge-tts ────────────────────────────────────────────────────

async def _edge(text: str, voice_label: str) -> tuple[bytes, str]:
    try:
        import edge_tts
    except ImportError:
        raise TTSError("edge-tts not installed: pip install edge-tts")

    voice = EDGE_VOICES.get(voice_label, EDGE_VOICES["narrator"])
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])

    mp3 = buf.getvalue()
    if not mp3:
        raise TTSError("edge-tts: empty audio returned — network may be unavailable")
    return mp3, "mp3"


# ─── Provider 2: gTTS (Google Translate TTS) ─────────────────────────────────

async def _gtts(text: str, voice_label: str) -> tuple[bytes, str]:
    try:
        from gtts import gTTS, gTTSError as GTTSError
    except ImportError:
        raise TTSError("gTTS not installed: pip install gTTS")

    tld = GTTS_TLDS.get(voice_label, "com")

    # gTTS is synchronous — run in executor so we don't block the event loop
    def _run():
        buf = io.BytesIO()
        tts = gTTS(text=text, lang="en", tld=tld, slow=False)
        tts.write_to_fp(buf)
        return buf.getvalue()

    loop = asyncio.get_event_loop()
    mp3 = await loop.run_in_executor(None, _run)

    if not mp3:
        raise TTSError("gTTS: empty audio returned")
    return mp3, "mp3"


# ─── Provider 3: pyttsx3 (offline, OS voices) ────────────────────────────────

async def _pyttsx3(text: str, voice_label: str) -> tuple[bytes, str]:
    try:
        import pyttsx3
    except ImportError:
        raise TTSError("pyttsx3 not installed: pip install pyttsx3")

    rate = PYTTSX3_RATES.get(voice_label, 165)
    tmp_wav = tempfile.mktemp(suffix=".wav")

    def _run():
        try:
            engine = pyttsx3.init()
        except Exception as e:
            raise TTSError(
                f"pyttsx3 could not initialize speech engine: {e}\n"
                "On Linux: sudo apt install espeak-ng\n"
                "On macOS: should work automatically (uses built-in voices)\n"
                "On Windows: should work automatically (uses SAPI5)"
            )

        engine.setProperty("rate", rate)

        # Pick a voice — names differ by OS:
        # macOS: Alex, Samantha, Daniel (NSSpeechSynthesizer)
        # Linux/espeak: en-us, en-gb, en+m3 etc.
        # Windows: voices contain "English" in name
        voices = engine.getProperty("voices") or []
        preferred = {"narrator": ["alex", "en-us", "english"],
                     "friendly": ["samantha", "en-gb", "english"],
                     "calm":     ["daniel", "en+m3", "english"]}
        targets = preferred.get(voice_label, ["english"])
        for v in voices:
            vname = (v.name or v.id or "").lower()
            if any(t in vname for t in targets):
                engine.setProperty("voice", v.id)
                break

        engine.save_to_file(text, tmp_wav)
        engine.runAndWait()
        engine.stop()

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _run)
    except TTSError:
        raise
    except Exception as e:
        raise TTSError(f"pyttsx3: {e}")

    if not os.path.exists(tmp_wav) or os.path.getsize(tmp_wav) < 100:
        raise TTSError("pyttsx3: failed to write audio file")

    with open(tmp_wav, "rb") as f:
        wav = f.read()
    try:
        os.unlink(tmp_wav)
    except OSError:
        pass
    return wav, "wav"


# ─── Provider 4: Gemini TTS (last resort — has quota) ────────────────────────

async def _gemini(text: str, voice_label: str) -> tuple[bytes, str]:
    if not settings.gemini_api_key:
        raise TTSError("Gemini TTS: GEMINI_API_KEY not set in backend/.env")

    voice_name = GEMINI_VOICES.get(voice_label, GEMINI_VOICES["narrator"])
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-tts:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}
            },
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload)

    if r.status_code == 429:
        raise TTSError("Gemini TTS: quota exceeded (429)")
    if r.status_code != 200:
        raise TTSError(f"Gemini TTS: HTTP {r.status_code}")

    data = r.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        b64   = next(p for p in parts if "inlineData" in p)["inlineData"]["data"]
    except (KeyError, IndexError, StopIteration) as e:
        raise TTSError(f"Gemini TTS: unexpected response shape ({e})")

    return _pcm_to_wav(base64.b64decode(b64)), "wav"


# ─── Public API ───────────────────────────────────────────────────────────────

_PROVIDERS = [
    ("edge-tts",  _edge),
    ("gTTS",      _gtts),
    ("pyttsx3",   _pyttsx3),
    ("Gemini TTS", _gemini),
]


async def synthesize(text: str, voice: str = "narrator") -> tuple[bytes, str]:
    """
    Returns (audio_bytes, extension).
    extension is 'mp3' or 'wav' depending on which provider succeeded.
    Tries all 4 providers in order. Raises TTSError only if every one fails.
    """
    errors = []
    for name, fn in _PROVIDERS:
        try:
            result = await fn(text, voice)
            # Log which provider succeeded (visible in uvicorn terminal)
            print(f"[MindFlow TTS] {name} succeeded for voice={voice!r}")
            return result
        except TTSError as e:
            errors.append(f"{name}: {e}")
            print(f"[MindFlow TTS] {name} failed: {e}")
        except Exception as e:
            errors.append(f"{name}: unexpected — {e}")
            print(f"[MindFlow TTS] {name} unexpected error: {e}")

    raise TTSError(
        "All 4 TTS providers failed:\n" +
        "\n".join(f"  • {e}" for e in errors) +
        "\n\nAt minimum, pyttsx3 should always work offline. "
        "Run: pip install pyttsx3"
    )
