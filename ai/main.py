"""FastAPI app for the conversational AI layer (chat now, voice next).

Mounts the existing core-backed REST routes (api/routes.py, /api/*) alongside the
new conversational endpoints, with CORS for the Next.js frontend. Run:

    uv run uvicorn ai.main:app --reload --port 7860

This is the AI service; the graded Gradio app (app.py) stays separate.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.routers.chat import router as chat_router
from api.routes import router as api_router

log = logging.getLogger(__name__)

app = FastAPI(title="SliceMatic AI", version="0.1.0")

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
app.include_router(chat_router)  # /chat


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "slicematic-ai"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
