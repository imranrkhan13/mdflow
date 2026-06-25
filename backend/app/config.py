"""
Settings loaded from environment variables.
- Locally: from backend/.env file
- On HF Spaces: from the Space's "Secrets" tab (set as env vars, no .env file)

.env is gitignored — never committed. Safe to push config.py.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Local .env path — only used locally. On HF Spaces the env vars come
# from the Secrets tab and are already in the environment, so the missing
# .env file is fine (pydantic-settings falls back to actual env vars).
_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    cohere_api_key: str | None = None
    mistral_api_key: str | None = None
    openrouter_api_key: str | None = None
    scaledown_api_key: str | None = None

    # CORS: accepts a comma-separated string or a JSON list.
    # On HF Spaces set: CORS_ORIGINS=https://your-app.vercel.app
    # Locally the default covers the Vite dev server.
    cors_origins_raw: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_origins_raw.strip()
        # Support JSON list format ["a","b"] or comma-separated a,b
        if raw.startswith("["):
            import json
            try:
                return json.loads(raw)
            except Exception:
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
