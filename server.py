"""Custom HTML frontend + API, one FastAPI process (Hugging Face Docker Space).

    uv run python server.py        ->  http://localhost:7861   (UI)
                                       http://localhost:7861/docs (API)

The static frontend in web/ calls the /api/* endpoints; all validation, pricing
and persistence happen in core/ via api/routes.py — identical to the Gradio app.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routes import router

app = FastAPI(title="SliceMatic", version="0.1.0")
app.include_router(router)

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
# html=True serves index.html at "/". Mounted last so /api/* takes precedence.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7861)))
