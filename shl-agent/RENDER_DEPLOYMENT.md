# Render Deployment Guide

## Quick Deploy (Recommended)

Render will auto-detect the `render.yaml` configuration. Just follow these steps:

### 1. Push to GitHub
```bash
git add .
git commit -m "Configure for Render deployment"
git push origin main
```

### 2. Create Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `Kisalay07/shl-assessment-agent`
4. Render will auto-detect `render.yaml` and pre-fill settings

### 3. Verify Auto-Detected Settings

Render should automatically configure:
- **Name**: `shl-assessment-agent-1`
- **Root Directory**: `shl-agent`
- **Environment**: `Python 3`
- **Build Command**: `bash render-build.sh`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
- **Region**: Oregon (or your preferred region)
- **Plan**: Free

### 4. Set Environment Variable

**CRITICAL**: Before deploying, add your Groq API key:

1. In the Render dashboard, go to **Environment** tab
2. Add environment variable:
   - **Key**: `GROQ_API_KEY`
   - **Value**: `gsk_...` (your actual Groq API key from https://console.groq.com)
3. Click **"Save Changes"**

### 5. Deploy

Click **"Create Web Service"** or **"Manual Deploy"**

The deployment will:
- Install Python 3.11.9
- Run the build script
- Install all dependencies
- Start the FastAPI server
- Health check at `/health`

### 6. Verify Deployment

Once deployed, test your endpoints:

```bash
# Health check
curl https://your-service.onrender.com/health
# Expected: {"status":"ok","catalog_items":XXX}

# Root endpoint
curl https://your-service.onrender.com/
# Expected: Service info with version and endpoints

# API docs
# Visit: https://your-service.onrender.com/docs
```

---

## Manual Configuration (If render.yaml is not detected)

If Render doesn't auto-detect the configuration, fill in manually:

### Form Fields:

| Field | Value |
|-------|-------|
| **Name** | `shl-assessment-agent-1` (or your preferred name) |
| **Root Directory** | `shl-agent` |
| **Environment** | `Python 3` |
| **Branch** | `main` |
| **Build Command** | `bash render-build.sh` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1` |
| **Region** | Oregon (or Virginia if you have other services there) |
| **Plan** | Free |

### Environment Variables:

Add these in the **Environment** tab:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_...` (your API key) ⚠️ **REQUIRED** |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` (auto-set) |
| `RETRIEVAL_TOP_K` | `25` (auto-set) |
| `LLM_MAX_TOKENS` | `1400` (auto-set) |
| `LLM_TEMPERATURE` | `0.05` (auto-set) |
| `PYTHONUNBUFFERED` | `1` (auto-set) |

---

## Troubleshooting

### Build Fails with "metadata-generation-failed"

**Solution**: The `render-build.sh` script handles this by:
- Upgrading pip, setuptools, and wheel first
- Using `--no-cache-dir` to avoid cache issues
- Installing pinned versions that are known to work

### "Read-only file system" errors

**Solution**: Fixed by:
- Setting `rootDir: shl-agent` in render.yaml
- Using `--no-cache-dir` flag
- Not writing to restricted directories

### Service shows "loading" status

**Cause**: Catalog is still initializing

**Solution**: Wait 5-10 seconds and retry. Check logs for errors.

### 503 Service Unavailable

**Causes**:
1. GROQ_API_KEY not set
2. Catalog failed to load
3. Service still starting

**Solution**:
1. Verify GROQ_API_KEY is set in Environment tab
2. Check logs for errors
3. Wait for startup to complete (~10-15 seconds)

### Logs show "GROQ_API_KEY not found"

**Solution**: 
1. Go to Render dashboard → Your service → Environment
2. Add `GROQ_API_KEY` with your actual key
3. Save and redeploy

---

## Performance Optimization

### Free Tier Limitations

- Service spins down after 15 minutes of inactivity
- First request after spin-down takes ~30-60 seconds (cold start)
- 750 hours/month free

### Keeping Service Warm (Optional)

Use a service like UptimeRobot or cron-job.org to ping your `/health` endpoint every 10 minutes:

```bash
curl https://your-service.onrender.com/health
```

### Upgrade to Paid Plan

For production use, consider upgrading to:
- **Starter Plan** ($7/month): No spin-down, faster builds
- **Standard Plan** ($25/month): More resources, better performance

---

## Monitoring

### View Logs

1. Go to Render dashboard → Your service
2. Click **"Logs"** tab
3. Monitor real-time logs

### Key Log Messages

- `✅ Ready — XXX assessments indexed.` = Service ready
- `⬆ Loading SHL catalog …` = Startup in progress
- `❌ Failed to initialize` = Critical error, check GROQ_API_KEY

### Health Check

Render automatically monitors `/health` endpoint:
- Returns 200 OK = Service healthy
- Returns 503 = Service loading or unhealthy

---

## Updating the Service

### Push Updates

```bash
git add .
git commit -m "Update service"
git push origin main
```

Render will automatically:
1. Detect the push
2. Rebuild the service
3. Deploy the new version
4. Zero-downtime deployment (on paid plans)

### Manual Deploy

1. Go to Render dashboard → Your service
2. Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Use Render's Environment Variables** - Encrypted at rest
3. **Rotate API keys regularly** - Update in Render dashboard
4. **Monitor logs** - Check for suspicious activity
5. **Enable HTTPS** - Render provides free SSL certificates

---

## Cost Estimation

### Free Tier
- **Cost**: $0/month
- **Limitations**: Spins down after 15 min inactivity
- **Best for**: Development, testing, low-traffic demos

### Starter Tier
- **Cost**: $7/month
- **Benefits**: Always on, no spin-down
- **Best for**: Production apps with moderate traffic

---

## Support

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Project Issues**: https://github.com/Kisalay07/shl-assessment-agent/issues

---

## Quick Reference

### Service URLs
- **Health**: `https://your-service.onrender.com/health`
- **API Docs**: `https://your-service.onrender.com/docs`
- **Chat Endpoint**: `POST https://your-service.onrender.com/chat`

### Important Files
- `render.yaml` - Deployment configuration
- `render-build.sh` - Build script
- `requirements.txt` - Python dependencies
- `.python-version` - Python version specification
- `runtime.txt` - Alternative Python version specification

### Environment Variables
- `GROQ_API_KEY` - **REQUIRED** - Your Groq API key
- `GROQ_MODEL` - LLM model to use
- `RETRIEVAL_TOP_K` - Number of BM25 results
- `LLM_MAX_TOKENS` - Max response tokens
- `LLM_TEMPERATURE` - LLM temperature (0-1)
