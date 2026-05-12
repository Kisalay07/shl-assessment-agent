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

1. Push to GitHub.
2. New Web Service → point at repo → Render auto-detects `render.yaml`.
3. Set `GROQ_API_KEY` in Render dashboard → Environment.
4. Deploy. `/health` returns `{"status":"ok"}` in ~5 s.

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
