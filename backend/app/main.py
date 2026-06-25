from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, _ENV_FILE
from app.routers import upload, explain, video

app = FastAPI(title="MindFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(explain.router)
app.include_router(video.router)


@app.on_event("startup")
async def log_provider_status():
    import os

    configured = {
        "GEMINI_API_KEY": bool(settings.gemini_api_key),
        "GROQ_API_KEY": bool(settings.groq_api_key),
        "MISTRAL_API_KEY": bool(settings.mistral_api_key),
        "COHERE_API_KEY": bool(settings.cohere_api_key),
        "OPENROUTER_API_KEY": bool(settings.openrouter_api_key),
    }
    print(f"\n[MindFlow] reading env from: {_ENV_FILE}")
    print(f"[MindFlow] .env file exists: {os.path.exists(_ENV_FILE)}")
    for name, ok in configured.items():
        print(f"[MindFlow] {name}: {'configured' if ok else 'MISSING'}")
    if not any(configured.values()):
        print(
            "[MindFlow] WARNING: no providers configured — check that "
            "backend/.env exists and variable names match exactly "
            "(GROQ not GROK, etc). See backend/.env.example.\n"
        )
    else:
        print()


@app.get("/api/health")
async def health():
    configured = {
        "gemini": bool(settings.gemini_api_key),
        "groq": bool(settings.groq_api_key),
        "mistral": bool(settings.mistral_api_key),
        "cohere": bool(settings.cohere_api_key),
        "openrouter": bool(settings.openrouter_api_key),
    }
    return {"status": "ok", "providers_configured": configured}
