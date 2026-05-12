# Deployment Guide

## Option 1: Render (Recommended)

1. Go to https://render.com and sign up
2. Click "New +" → "Web Service"
3. Connect your Git repository
4. Configure:
   - **Root Directory**: `shl-agent`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variable:
   - **Key**: `GROQ_API_KEY`
   - **Value**: Your Groq API key from https://console.groq.com
6. Click "Create Web Service"
7. Wait 2-3 minutes for deployment

Your service will be available at: `https://your-service.onrender.com`

## Option 2: Railway

1. Go to https://railway.app and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Add environment variable:
   - **Key**: `GROQ_API_KEY`
   - **Value**: Your Groq API key
5. Railway auto-deploys

## Option 3: Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
cd shl-agent
fly auth login
fly launch --no-deploy
fly secrets set GROQ_API_KEY=your_key_here
fly deploy
```

## Testing Your Deployment

```bash
# Health check
curl https://your-url/health

# Chat endpoint
curl -X POST https://your-url/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need assessments for a senior engineer"}]}'
```

## Troubleshooting

- **Build fails**: Verify `requirements.txt` is present
- **503 errors**: Check logs for catalog loading errors
- **Timeouts**: Groq free tier has rate limits, wait between requests
