"""
Cascading LLM router.

Tries providers in order until one succeeds. Each provider is wrapped so
that failures (missing key, rate limit, timeout, bad response) fall through
to the next provider rather than failing the request outright.

Order is chosen for a mix of speed (Groq), quality (Gemini), and breadth
of fallback coverage (Mistral, Cohere, OpenRouter as a final catch-all
since it can reach many backend models).
"""
import httpx
from app.config import settings


class ProviderError(Exception):
    pass


async def _call_gemini(prompt: str, system: str) -> str:
    if not settings.gemini_api_key:
        raise ProviderError("gemini: no key configured")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload)
        if r.status_code != 200:
            raise ProviderError(f"gemini: {r.status_code} {r.text[:200]}")
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"gemini: unexpected response shape {e}")


async def _call_groq(prompt: str, system: str) -> str:
    if not settings.groq_api_key:
        raise ProviderError("groq: no key configured")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            raise ProviderError(f"groq: {r.status_code} {r.text[:200]}")
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"groq: unexpected response shape {e}")


async def _call_mistral(prompt: str, system: str) -> str:
    if not settings.mistral_api_key:
        raise ProviderError("mistral: no key configured")
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.mistral_api_key}"}
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            raise ProviderError(f"mistral: {r.status_code} {r.text[:200]}")
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"mistral: unexpected response shape {e}")


async def _call_cohere(prompt: str, system: str) -> str:
    if not settings.cohere_api_key:
        raise ProviderError("cohere: no key configured")
    url = "https://api.cohere.com/v2/chat"
    headers = {"Authorization": f"Bearer {settings.cohere_api_key}"}
    payload = {
        "model": "command-r-plus",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            raise ProviderError(f"cohere: {r.status_code} {r.text[:200]}")
        data = r.json()
        try:
            return data["message"]["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"cohere: unexpected response shape {e}")


async def _call_openrouter(prompt: str, system: str) -> str:
    if not settings.openrouter_api_key:
        raise ProviderError("openrouter: no key configured")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}
    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            raise ProviderError(f"openrouter: {r.status_code} {r.text[:200]}")
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"openrouter: unexpected response shape {e}")


PROVIDER_CHAIN = [
    ("gemini", _call_gemini),
    ("groq", _call_groq),
    ("mistral", _call_mistral),
    ("cohere", _call_cohere),
    ("openrouter", _call_openrouter),
]


async def generate(prompt: str, system: str = "You are a helpful assistant.") -> dict:
    """
    Walks the provider chain in order. Returns the first successful
    response along with which provider served it (useful for the UI to
    show a small 'served by groq' style badge, and for debugging).
    """
    errors = []
    for name, fn in PROVIDER_CHAIN:
        try:
            text = await fn(prompt, system)
            return {"text": text, "provider": name, "errors": errors}
        except ProviderError as e:
            errors.append(str(e))
            continue
        except httpx.RequestError as e:
            errors.append(f"{name}: network error {e}")
            continue
    raise ProviderError(
        "All providers failed: " + " | ".join(errors)
        if errors
        else "No providers configured"
    )
