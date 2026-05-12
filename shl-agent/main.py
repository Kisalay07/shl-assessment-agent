"""
SHL Assessment Agent — FastAPI service.
GET  /health  → {"status": "ok"}
POST /chat    → ChatResponse (stateless; full history in every request)
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent import Agent
from app.catalog import CatalogStore
from app.models import ChatRequest, ChatResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

_catalog: CatalogStore | None = None
_agent:   Agent | None        = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _catalog, _agent
    try:
        logger.info("⬆  Loading SHL catalog …")
        _catalog = CatalogStore()
        await _catalog.load()
        _agent = Agent(_catalog)
        logger.info("✅ Ready — %d assessments indexed.", len(_catalog.items))
        yield
    except Exception as e:
        logger.error("❌ Failed to initialize: %s", e, exc_info=True)
        raise
    finally:
        logger.info("⬇  Shutting down.")


app = FastAPI(
    title="SHL Assessment Agent",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _global_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "SHL Assessment Agent",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    if _agent is None:
        return JSONResponse(status_code=503, content={"status": "loading"})
    return {"status": "ok", "catalog_items": len(_catalog.items)}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if _agent is None:
        raise HTTPException(503, "Catalog is still loading — retry in a moment.")
    if len(req.messages) > 8:
        raise HTTPException(400, "Conversation exceeds the 8-turn limit.")
    if not any(m.role == "user" for m in req.messages):
        raise HTTPException(400, "At least one user message is required.")
    return await _agent.chat(req.messages)
