"""FastAPI app for the conversational AI layer (chat now, voice next).

Mounts the existing core-backed REST routes (api/routes.py, /api/*) alongside the
new conversational endpoints, with CORS for the Next.js frontend. Run:

    uv run uvicorn ai.main:app --reload --port 7860

This is the AI service; the graded Gradio app (app.py) stays separate.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.admin_routes import router as admin_router
from api.staff_routes import router as staff_router
from ai.routers.chat import router as chat_router
from ai.routers.voice import router as voice_router
from api.routes import router as api_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up clients + the OpenRouter connection at boot so the first real
    request is fast (otherwise it eats ~7-19s of cold-start). Best-effort: a
    warmup failure (no keys/network) must never stop the server from starting.
    """
    try:
        from ai import observability, tools
        from ai.config import get_settings
        from ai.llm import get_client
        from db.client import get_client as get_db

        settings = get_settings()
        observability.get_langfuse()
        get_db()
        tools._load_active_menu()
        get_client().chat.completions.create(
            model=settings.primary_model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        log.info("AI warmup complete")
    except Exception as exc:
        log.warning("AI warmup skipped: %s", exc)
    yield


app = FastAPI(title="SliceMatic AI", version="0.1.0", lifespan=lifespan)

# CORS for the Next.js frontend. Comma-separated origins in AI_CORS_ORIGINS,
# default "*" for the demo (we use no cookies, so wildcard is fine).
_origins = [
    o.strip() for o in os.environ.get("AI_CORS_ORIGINS", "*").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)  # /api/* (menu, summary, order, analytics, ...)
app.include_router(admin_router)  # /admin/* protected owner/ops APIs
app.include_router(staff_router)  # /staff/* protected kitchen/backstage APIs
app.include_router(chat_router)  # /chat
app.include_router(voice_router)  # /voice/transcribe, /voice/respond, /voice/synthesize


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "slicematic-ai"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
