# MindFlow — Vertical Slice

This is **one fully working slice** of the MindFlow spec: upload a markdown
file (README, ARCHITECTURE.md, etc.) → it's parsed into a heading hierarchy
→ a graph is built (structural edges from headings, inferred "concept"
edges where sections share a detected system term like "Database" or
"API") → the graph renders as an interactive React Flow canvas → clicking
a node calls a real AI provider to explain it, with four modes (Explain,
Analogy, Interview questions, Common mistakes) — **plus** a narrated,
AI-scripted, code-animated explainer video per node.

It is **not** the full MindFlow product. PDF/DOCX/source-code/OpenAPI
parsing, execution-flow animation across the whole graph, flashcards,
GitHub import, and the other modes in the original spec are not built
here — see "What's not built" below.

## Design: white / brown / Inter

The UI is a warm paper-white base (`#fdfcfa`) with a deep umber/espresso
ink (`#3d2b1f`) and clay accent (`#b5673f`), set in Inter throughout
(JetBrains Mono reserved for code/labels/data, matching the pattern a lot
of dev-tool-y YC products use: humanist sans for reading, mono for
"this is data"). Token system lives in `frontend/tailwind.config.js`
under `paper` / `umber` / `clay` / `sage`.

## The "video" feature — what it actually is

You asked for free AI-generated narrated explainer videos using the 5
configured providers (Gemini, Groq, Mistral, Cohere, OpenRouter). Worth
being precise about what that combination can and can't do:

- **Script**: real LLM generation, via the same 5-provider fallback router
  used for the Explain panel (`backend/app/services/script_generator.py`).
  Asks for structured JSON "beats" (narration + visual instruction +
  emphasis word) rather than one paragraph, so visuals can sync to speech.
- **Voiceover**: real AI generation, via Gemini's TTS model
  (`gemini-2.5-flash-preview-tts`), free-tier accessible with a Gemini API
  key. This is the only one of the 5 providers with a speech model, so
  there's no fallback chain for this step — if Gemini's not configured,
  video generation fails with a clear error rather than silently
  degrading.
- **Visuals**: **not** AI-generated. None of the 5 providers generate
  video or images. The visuals are deterministic, code-drawn motion
  graphics (Pillow-rendered frames, themed to match the app exactly,
  encoded with ffmpeg) — title cards, a node-and-its-connections diagram
  with a soft pulsing glow, a code-reveal panel, a summary card. Each
  beat's visual duration is timed to that beat's actual synthesized
  speech length, so narration and motion stay in sync without hand-tuned
  timing.

I'm flagging this distinction because "AI-generated video" implies the
pixels themselves came from a generative model, and that's not what's
happening here — calling it that in a resume bullet or pitch deck would
overstate it. "AI-narrated, code-animated explainer" is the accurate
description, and it's a legitimate, free, working feature — just not
AI-rendered animation.

**Pipeline**: `backend/app/services/video/`
- `frame_renderer.py` — Pillow drawing functions for each visual type
- `renderer.py` — orchestrates per-beat TTS → duration measurement →
  synced frame rendering → audio concat → ffmpeg mux into one MP4
- `jobs.py` — in-memory job tracking, since rendering takes real wall
  time (sequential TTS calls + frame rendering + encode), so it runs as
  a background task polled by the frontend rather than blocking one
  request

**What I tested**: the full pipeline end-to-end with real network access
blocked in my sandbox (only `pypi.org`/`npmjs.com`/`github.com`-class
domains are reachable there, not the AI provider APIs) — so I validated
TTS response parsing and WAV-wrapping logic directly, then ran the
complete renderer (frame timing, ffmpeg concat, mux) with synthetic
audio standing in for real Gemini TTS output, confirming a valid
1280×720/30fps H.264 + AAC MP4 with correctly beat-synced visuals. The
actual live call to Gemini's TTS endpoint — request shape and auth are
code-reviewed and match Google's documented format — I could not
execute from inside this sandbox; worth your own first real run.

## Why the architecture looks like this (keys)

The original request included five live API keys pasted directly into
chat, with instructions to use them as `VITE_*` frontend env vars. I did
not do that: Vite inlines `VITE_*` variables into the JS bundle shipped
to every browser, so any visitor could read them out of dev tools.

Instead, keys live only in `backend/.env` (gitignored, never committed,
never sent to the browser), and FastAPI is the only thing that calls
external AI providers. Since those keys were posted in this conversation,
rotating them on each provider's dashboard before relying on this
anywhere beyond local testing is still worth doing.

## Running it
cp .env.example .env
**Backend:**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# edit .env and paste your (rotated) keys in — Gemini specifically is
# required for video generation (TTS); any one of the 5 is enough for
# the Explain panel and script generation

```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Drop a `.md` file, click a node, use the
mode tabs to get an AI explanation, or scroll down in the right panel to
generate a narrated video for that node.

ffmpeg must be installed and on PATH (`ffmpeg -version` to check) — it's
used for audio concatenation and final video encoding.

## What's actually built

- `backend/app/parsers/markdown_parser.py` — heading hierarchy + code
  block extraction + naive concept keyword detection
- `backend/app/services/graph_builder.py` — NetworkX graph, layered
  layout, structural + concept edges, serialized to React Flow shape
- `backend/app/services/ai_router.py` — 5-provider cascading fallback
  for text generation
- `backend/app/services/tts.py` — Gemini TTS client, PCM→WAV wrapping
- `backend/app/services/script_generator.py` — structured narration
  script generation (beats) via the AI router
- `backend/app/services/video/` — frame rendering + render orchestration
  + job tracking for the explainer video pipeline
- `backend/app/routers/{upload,explain,video}.py` — the real endpoints
- `frontend/src/pages/Landing.jsx` — hero, drag-drop upload, ambient
  canvas graph background
- `frontend/src/pages/Workspace.jsx` — three-pane layout
- `frontend/src/components/ConceptNode.jsx` — custom React Flow node
- `frontend/src/components/ExplainPanel.jsx` — mode tabs + AI explanation
- `frontend/src/components/VideoPanel.jsx` — voice picker, generation
  progress, player, download

## What's not built (was in the original spec, scoped out for this slice)

PDF/DOCX/source-code (Tree-sitter)/OpenAPI/Mermaid parsing · GitHub repo
import · full-graph animated execution-flow mode with traveling particles
· timeline scrubber · flashcard mode · interview mode with voice/AI
evaluation · multiple visualization types (ER diagram, sequence diagram,
deployment diagram, etc.) · semantic search · persistence beyond
in-memory (the spec calls for SQLite → Postgres later) · auth/multi-user.

## Files you should not commit

`backend/.env` is gitignored. Don't remove that line. If you ever push
this to GitHub, double check `git status` shows `.env` as ignored before
your first commit.

