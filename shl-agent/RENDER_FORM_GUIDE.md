# Render Deployment Form - Quick Reference

## 🎯 What to Fill in the Render Form

When creating a new Web Service on Render, use these exact values:

---

### Basic Settings

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `shl-assessment-agent-1` | Or any unique name you prefer |
| **Project** | _(Optional)_ | Leave empty or select existing project |
| **Environment** | _(Optional)_ | Leave empty or select existing environment |
| **Language** | `Python 3` | Auto-detected |
| **Branch** | `main` | The Git branch to deploy |
| **Region** | `Virginia (US East)` or `Oregon` | Choose based on your location |

---

### Advanced Settings

| Field | Value | Required? |
|-------|-------|-----------|
| **Root Directory** | `shl-agent` | ✅ **CRITICAL** - Must be set! |
| **Build Command** | `bash render-build.sh` | ✅ **CRITICAL** - Custom build script |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1` | ✅ **CRITICAL** - Starts the server |

---

### Environment Variables

⚠️ **IMPORTANT**: Add these in the "Environment" tab BEFORE deploying:

| Key | Value | Required? |
|-----|-------|-----------|
| `GROQ_API_KEY` | `gsk_...` (your actual API key) | ✅ **REQUIRED** - Get from https://console.groq.com |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | ✅ Auto-set by render.yaml |
| `RETRIEVAL_TOP_K` | `25` | ✅ Auto-set by render.yaml |
| `LLM_MAX_TOKENS` | `1400` | ✅ Auto-set by render.yaml |
| `LLM_TEMPERATURE` | `0.05` | ✅ Auto-set by render.yaml |
| `PYTHONUNBUFFERED` | `1` | ✅ Auto-set by render.yaml |

---

## 📋 Step-by-Step Checklist

### Before You Start
- [ ] Code is pushed to GitHub (`git push origin main`)
- [ ] You have a Groq API key from https://console.groq.com

### On Render Dashboard
1. [ ] Click "New +" → "Web Service"
2. [ ] Connect your GitHub repository: `Kisalay07/shl-assessment-agent`
3. [ ] Verify Render auto-detected `render.yaml` (should show "Blueprint detected")

### Verify Auto-Filled Settings
4. [ ] **Name**: `shl-assessment-agent-1` (or your custom name)
5. [ ] **Root Directory**: `shl-agent` ⚠️ **MUST BE SET**
6. [ ] **Build Command**: `bash render-build.sh`
7. [ ] **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
8. [ ] **Region**: Virginia or Oregon (your choice)
9. [ ] **Plan**: Free

### Add Environment Variable
10. [ ] Go to "Environment" tab
11. [ ] Click "Add Environment Variable"
12. [ ] Key: `GROQ_API_KEY`
13. [ ] Value: Your actual Groq API key (starts with `gsk_`)
14. [ ] Click "Save Changes"

### Deploy
15. [ ] Click "Create Web Service" button
16. [ ] Wait 2-3 minutes for build to complete
17. [ ] Check logs for "✅ Ready — XXX assessments indexed."

### Verify Deployment
18. [ ] Visit `https://your-service.onrender.com/health`
19. [ ] Should return: `{"status":"ok","catalog_items":XXX}`
20. [ ] Visit `https://your-service.onrender.com/docs` for API documentation

---

## 🚨 Common Mistakes to Avoid

### ❌ DON'T
- Leave **Root Directory** empty → Will cause "file not found" errors
- Forget to add **GROQ_API_KEY** → Service will fail to start
- Use wrong Build Command → Will cause build failures
- Deploy without pushing to GitHub first → Will deploy old code

### ✅ DO
- Set **Root Directory** to `shl-agent`
- Add **GROQ_API_KEY** before deploying
- Use the exact commands from this guide
- Push code to GitHub before creating service

---

## 🔍 Troubleshooting

### "File not found" or "No such file or directory"
**Problem**: Root Directory not set  
**Solution**: Set Root Directory to `shl-agent`

### "GROQ_API_KEY not found"
**Problem**: Environment variable not set  
**Solution**: Add GROQ_API_KEY in Environment tab

### Build fails with "metadata-generation-failed"
**Problem**: Old build process  
**Solution**: Ensure Build Command is `bash render-build.sh`

### Service shows 503 error
**Problem**: Service still starting or failed to start  
**Solution**: 
1. Wait 10-15 seconds for startup
2. Check logs for errors
3. Verify GROQ_API_KEY is set correctly

---

## 📞 Need Help?

1. **Check logs**: Render Dashboard → Your Service → Logs tab
2. **Read detailed guide**: [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
3. **Render docs**: https://render.com/docs
4. **Project issues**: https://github.com/Kisalay07/shl-assessment-agent/issues

---

## ✨ Success Indicators

You'll know deployment succeeded when you see:

### In Logs:
```
✅ Ready — XXX assessments indexed.
```

### At /health endpoint:
```json
{
  "status": "ok",
  "catalog_items": 123
}
```

### At / (root) endpoint:
```json
{
  "service": "SHL Assessment Agent",
  "version": "2.0.0",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "chat": "/chat",
    "docs": "/docs"
  }
}
```

---

## 🎉 You're Done!

Your SHL Assessment Agent is now live on Render!

**Next steps**:
- Test the `/chat` endpoint with Postman or curl
- Visit `/docs` for interactive API documentation
- Monitor logs for any issues
- Consider upgrading to paid plan for production use (no spin-down)
