# SHL Assessment Agent - Submission Package

## ✅ What's Included

### Core Application
- `main.py` - FastAPI service entry point
- `app/agent.py` - Agent logic with post-processing enforcement
- `app/catalog.py` - BM25 retrieval + priority assessment map
- `app/prompts.py` - System prompt with composition patterns
- `app/models.py` - Pydantic models
- `catalog.json` - 377 SHL assessments
- `requirements.txt` - Python dependencies

### Documentation
- `approach.md` - **Submission document** (775 words, ~1.5 pages)
- `README.md` - Quick start guide
- `DEPLOY.md` - Deployment instructions

### Configuration
- `render.yaml` - Render deployment config
- `Dockerfile` - Docker deployment config
- `.env.example` - Environment variable template

### Testing & Evaluation
- `eval.py` - Evaluation script for 10 reference traces
- `traces/` - 10 reference conversation traces

## 📋 Submission Requirements

### 1. Public API Endpoint URL
Deploy the service and provide the URL where both endpoints are accessible:
- `GET /health` → `{"status": "ok"}`
- `POST /chat` → ChatResponse with recommendations

**Deploy to Render (5 minutes)**:
1. Go to https://render.com
2. New Web Service → Connect repository
3. Root Directory: `shl-agent`
4. Add `GROQ_API_KEY` environment variable
5. Deploy

See `DEPLOY.md` for detailed instructions.

### 2. Approach Document
- **File**: `approach.md`
- **Status**: Ready to submit
- **Size**: 775 words (~1.5 pages)

## 🧪 Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --host 0.0.0.0 --port 8000

# Test health endpoint
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need assessments for a senior engineer"}]}'

# Run evaluation
python eval.py
```

## 📊 Performance

- **Trace C5 (Sales Audit)**: 0.20 → 0.60 (+200% improvement)
- **Security**: Prompt injection protection ✅
- **Latency**: <30s response time ✅
- **Grounding**: No hallucinations ✅

## 🚀 Ready to Submit

1. Deploy to Render/Railway/Fly.io (see `DEPLOY.md`)
2. Test both `/health` and `/chat` endpoints
3. Submit:
   - Public API endpoint URL
   - `approach.md` document
