# Deploying MindFlow — Free, Fully Working

## Architecture

```
Browser → Vercel (React frontend)
              ↓
       HF Spaces (FastAPI backend, Docker, ffmpeg installed)
              ↓
    AI providers (Gemini, Groq, Mistral, Cohere, OpenRouter)
```

Both are genuinely free. No credit card. No expiry.

---

## Part 1 — Deploy the Backend (Hugging Face Spaces)

### Step 1: Create the Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Space name**: `mindflow-backend` (or anything you like)
   - **License**: MIT
   - **SDK**: Docker  ← important, must be Docker not Gradio
   - **Visibility**: Public (required for free tier)
3. Click **Create Space**

### Step 2: Clone the Space repo locally

```bash
# Replace YOUR_USERNAME with your HF username
git clone https://huggingface.co/spaces/YOUR_USERNAME/mindflow-backend
cd mindflow-backend
```

### Step 3: Copy backend files into it

```bash
# From your mindflow project root:
cp -r backend/app               mindflow-backend/app
cp backend/Dockerfile           mindflow-backend/Dockerfile
cp backend/requirements.txt     mindflow-backend/requirements.txt
cp backend/README.md            mindflow-backend/README.md
cp backend/.gitignore           mindflow-backend/.gitignore

# DO NOT copy .env — keys go in HF Secrets (Step 5)
```

### Step 4: Push to HF Spaces

```bash
cd mindflow-backend
git add .
git commit -m "deploy mindflow backend"
git push
```

HF Spaces will now build your Docker image automatically.
Watch the build logs at: https://huggingface.co/spaces/YOUR_USERNAME/mindflow-backend

Build takes ~3-5 minutes (first time, installs ffmpeg + all Python packages).

### Step 5: Add your API keys as Secrets

In your Space: **Settings → Variables and Secrets → New Secret**

Add each one:
```
GEMINI_API_KEY     = your key
GROQ_API_KEY       = your key  
MISTRAL_API_KEY    = your key
COHERE_API_KEY     = your key
OPENROUTER_API_KEY = your key
CORS_ORIGINS_RAW   = https://YOUR-APP.vercel.app
```

⚠️ `CORS_ORIGINS_RAW` must match your Vercel URL exactly (no trailing slash).
You can add it after deploying the frontend in Part 2.

After adding secrets: **Factory reboot** the Space so it picks them up.

### Step 6: Get your backend URL

Your backend will be live at:
```
https://YOUR_USERNAME-mindflow-backend.hf.space
```

Test it:
```bash
curl https://YOUR_USERNAME-mindflow-backend.hf.space/api/health
```

Should return all providers as `true`.

---

## Part 2 — Deploy the Frontend (Vercel)

### Step 1: Push frontend to GitHub

```bash
# In your mindflow/frontend folder
cd frontend
git init
git add .
git commit -m "mindflow frontend"
gh repo create mindflow-frontend --public --push --source=.
# Or manually create a GitHub repo and push
```

### Step 2: Import to Vercel

1. Go to https://vercel.com/new
2. Import your `mindflow-frontend` GitHub repo
3. Framework preset: **Vite** (auto-detected)
4. Click **Environment Variables** and add:
   ```
   VITE_API_URL = https://YOUR_USERNAME-mindflow-backend.hf.space
   ```
   ← No trailing slash. This is not a secret — it's a public URL.
5. Click **Deploy**

Vercel builds in ~60 seconds. Your app is live at:
```
https://mindflow-frontend.vercel.app
```

### Step 3: Update CORS on HF Spaces

Go back to your HF Space Secrets and update:
```
CORS_ORIGINS_RAW = https://mindflow-frontend.vercel.app
```

Factory reboot the Space.

---

## Testing the full deployment

```bash
# 1. Health check
curl https://YOUR_USERNAME-mindflow-backend.hf.space/api/health

# 2. Upload test
curl -X POST https://YOUR_USERNAME-mindflow-backend.hf.space/api/upload \
  -F "file=@README.md"

# 3. Open your Vercel URL and try uploading a .md file
```

---

## What works on free tier

| Feature              | Works? | Notes                                    |
|----------------------|--------|------------------------------------------|
| Upload + graph       | ✅     | Full parse + NetworkX graph              |
| AI explanations      | ✅     | All 5 provider fallback chain            |
| Interview prep       | ✅     | Full project-level guide                 |
| Architecture map     | ✅     | Plain-English system explanation         |
| Video generation     | ✅     | edge-tts → gTTS → pyttsx3 → Gemini      |
| ffmpeg               | ✅     | Installed in Docker image                |
| Persistent storage   | ❌     | Videos live in /tmp, gone on restart     |
| Always-on            | ⚠️     | Free Spaces sleep after ~30min idle      |

## The only real limitation

Free HF Spaces sleep after ~30 minutes of no traffic. The first request
after sleep takes ~30-60 seconds to wake up (you'll see a loading spinner).
After that it's fast. For a portfolio piece this is totally fine.

To prevent sleeping: ping the health endpoint every 25 minutes.
Free option: https://cron-job.org (set up a free cron job to hit /api/health)

---

## Local development (unchanged)

```bash
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend  
cd frontend
npm run dev
```

Vite proxies /api → localhost:8000 locally, so no env var needed.
