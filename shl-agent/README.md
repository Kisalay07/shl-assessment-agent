# SHL Assessment Agent v2

Conversational FastAPI service that guides hiring managers to the right SHL Individual
Test Solutions through dialogue.

## Quick start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add your GROQ_API_KEY (free: https://console.groq.com)

# 3. Run (catalog.json is bundled — no internet needed at startup)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Health check
curl http://localhost:8000/health
# {"status": "ok"}
```

## API

### POST /chat
```json
{
  "messages": [
    {"role": "user", "content": "Hiring a senior Java developer who works with stakeholders"},
    {"role": "assistant", "content": "Is this for selection or development?"},
    {"role": "user", "content": "Selection, mid-level, around 4 years experience"}
  ]
}
```
Response:
```json
{
  "reply": "Here are 5 assessments ...",
  "recommendations": [
    {"name": "Java 8 (New)", "url": "https://www.shl.com/...", "test_type": "K"},
    {"name": "Occupational Personality Questionnaire OPQ32r", "url": "...", "test_type": "P"}
  ],
  "end_of_conversation": false
}
```

## Evaluate against all 10 reference traces

```bash
# Ensure the service is running, then:
python eval.py

# Single trace
python eval.py --trace traces/trace_C1_leadership.json
```

## Deploy to Render (free)

### Quick Deploy (Recommended)

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Create Web Service on Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your repository
   - Render auto-detects `render.yaml` configuration

3. **Set Environment Variable**
   - In Render dashboard → Environment tab
   - Add: `GROQ_API_KEY` = `gsk_...` (your key from https://console.groq.com)
   - Click "Save Changes"

4. **Deploy**
   - Click "Create Web Service"
   - Wait ~2-3 minutes for build
   - Service will be available at `https://your-service.onrender.com`

5. **Verify**
   ```bash
   curl https://your-service.onrender.com/health
   # Expected: {"status":"ok","catalog_items":XXX}
   ```

📖 **Detailed guide**: See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for troubleshooting and advanced configuration.

### Manual Configuration

If auto-detection fails, use these settings:

| Field | Value |
|-------|-------|
| Root Directory | `shl-agent` |
| Build Command | `bash render-build.sh` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1` |

## Deploy with Docker

```bash
docker build -t shl-agent .
docker run -p 8000:8000 -e GROQ_API_KEY=gsk_... shl-agent
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | **Required** |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model |
| `RETRIEVAL_TOP_K` | `25` | BM25 hits passed to LLM |
| `LLM_MAX_TOKENS` | `1400` | Max tokens in response |
| `LLM_TEMPERATURE` | `0.05` | Lower = more deterministic |
