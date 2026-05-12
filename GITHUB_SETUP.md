# GitHub Setup & Deployment Guide

## Step 1: Initialize Git Repository

```bash
# Initialize git
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: SHL Assessment Agent"
```

## Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository:
   - **Name**: `shl-assessment-agent` (or your choice)
   - **Visibility**: Private (recommended) or Public
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
3. Click "Create repository"

## Step 3: Push to GitHub

GitHub will show you commands. Use these:

```bash
# Add GitHub as remote
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Example:**
```bash
git remote add origin https://github.com/johndoe/shl-assessment-agent.git
git branch -M main
git push -u origin main
```

## Step 4: Deploy to Render

### Option A: Deploy from GitHub (Recommended)

1. Go to https://render.com and sign up
2. Click "New +" → "Web Service"
3. Click "Connect GitHub" and authorize Render
4. Select your repository: `shl-assessment-agent`
5. Configure:
   - **Name**: `shl-assessment-agent`
   - **Root Directory**: `shl-agent`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variable:
   - Click "Environment" tab
   - Add: `GROQ_API_KEY` = `your_groq_api_key_here`
7. Click "Create Web Service"
8. Wait 2-3 minutes for deployment
9. Your URL: `https://shl-assessment-agent-XXXX.onrender.com`

### Option B: Deploy without GitHub (Manual Upload)

If you don't want to use GitHub:

1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Choose "Deploy from Git" → "Public Git repository"
4. Or use Render's manual upload feature
5. Follow same configuration as above

## Step 5: Test Your Deployment

```bash
# Health check
curl https://your-service.onrender.com/health

# Chat endpoint
curl -X POST https://your-service.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need assessments for a senior engineer"}]}'
```

## Step 6: Submit

Once deployed and tested, submit:
1. **Public API Endpoint URL**: `https://your-service.onrender.com`
2. **Approach Document**: `shl-agent/approach.md`

---

## Quick Commands Summary

```bash
# 1. Initialize and commit
git init
git add .
git commit -m "Initial commit: SHL Assessment Agent"

# 2. Push to GitHub (replace with your repo URL)
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git branch -M main
git push -u origin main

# 3. Deploy on Render (via web interface)
# - Connect GitHub repo
# - Set root directory: shl-agent
# - Add GROQ_API_KEY environment variable
# - Deploy

# 4. Test
curl https://your-url.onrender.com/health
```

---

## Troubleshooting

### "fatal: not a git repository"
Run `git init` first.

### "Permission denied (publickey)"
Use HTTPS instead of SSH:
```bash
git remote set-url origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
```

### ".env file pushed to GitHub"
The `.gitignore` file prevents this. Verify with:
```bash
git status
# Should NOT show .env file
```

### "Build failed on Render"
- Check that Root Directory is set to `shl-agent`
- Verify `requirements.txt` exists in `shl-agent/`
- Check build logs for specific errors

---

## Alternative: Deploy without GitHub

If you prefer not to use GitHub, you can:

1. **Railway**: Upload code directly
2. **Fly.io**: Deploy via CLI (no GitHub needed)
3. **Docker**: Build and deploy container

See `shl-agent/DEPLOY.md` for details.
