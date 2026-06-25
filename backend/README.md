---
title: MindFlow Backend
emoji: 🧠
colorFrom: orange
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# MindFlow Backend API

FastAPI backend for MindFlow — transforms markdown documentation into
interactive visual mental models.

## Endpoints

- `POST /api/upload` — upload a markdown file, get back a graph
- `POST /api/explain` — AI explanation for a graph node
- `POST /api/explain/interview` — full project interview prep
- `POST /api/explain/architecture` — plain-English architecture explanation
- `POST /api/video/generate` — kick off narrated explainer video generation
- `GET /api/video/status/{job_id}` — poll job progress
- `GET /api/video/download/{job_id}` — download the finished MP4

## Environment Variables (set in HF Space Secrets tab)

```
GEMINI_API_KEY=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
COHERE_API_KEY=...
OPENROUTER_API_KEY=...
```
