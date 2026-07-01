# SliceMatic — Local Setup

How to run the whole project on a fresh machine. Written so a human **or** an LLM
agent can follow it top to bottom. For architecture and conventions, read
`CLAUDE.md`; this file is only about getting the servers up.

---

## What you'll run (3 servers)

| # | Server | Command (from repo root) | Port | What it is |
|---|--------|--------------------------|------|------------|
| 1 | **Gradio ordering app** | `uv run python app.py` | **7860** | The Stage-2 graded app (pure `core/` brain + Gradio UI). Standalone — needs **no** API keys. |
| 2 | **AI service (FastAPI)** | `uv run uvicorn ai.main:app --port 7861` | **7861** | Stage-3 conversational layer: `POST /chat`, `/voice/*`, and the shared `/api/*` (menu, cart, checkout). Chat needs an OpenRouter key; voice needs Deepgram. |
| 3 | **Next.js frontend** | `cd frontend && npm run dev` | **3000** | The customer web app (chat, menu, cart, checkout, orders, profile). Talks to server #2 over HTTP. |

**Dependencies between them:**
- The **frontend (3000)** needs the **AI service (7861)** running (chat, menu, pricing, checkout all call it).
- The **Gradio app (7860)** is fully independent — it doesn't need the other two.
- Servers 1 and 2 both import the same `core/` brain in-process; there's no HTTP between them.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **uv** | ≥ 0.11 | Python package/venv manager. Install: <https://docs.astral.sh/uv/> |
| **Python** | ≥ 3.12 | `uv` will fetch/pin it if missing. |
| **Node.js** | ≥ 20 (tested on 24) | For the frontend. |
| **npm** | ≥ 10 | Ships with Node. |

Check them:
```bash
uv --version
node --version
npm --version
```

---

## 1. Get the code

```bash
git clone <repo-url> pizzaflow
cd pizzaflow
```

## 2. Configure environment variables

### a) Backend — root `.env`
Copy the template and fill in keys:
```bash
cp .env.example .env      # (Windows PowerShell: Copy-Item .env.example .env)
```

Which keys you actually need depends on what you want to run:

| Feature | Required key(s) | If missing |
|---------|-----------------|------------|
| **Gradio app (7860)** | *none* | Works out of the box. |
| **Text chat** (frontend + `/chat`) | `OPENROUTER_API_KEY` | Chat can't reach the LLM. |
| **Voice** (`/voice/*`) | `DEEPGRAM_API_KEY` | Voice STT/TTS disabled; chat still works. |
| **Orders/session mirror** | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Optional — best-effort; `.txt` log stays primary. |
| **Tracing** | `LANGFUSE_*` | Optional — no-op if absent. |

Models default to `google/gemini-2.5-flash` with fallbacks (see `.env.example`).
Everything except `OPENROUTER_API_KEY` (for chat) and `DEEPGRAM_API_KEY` (for voice)
is optional — the app degrades gracefully.

### b) Frontend — `frontend/.env.local` (optional)
The frontend **defaults to `http://localhost:7861` in code**, so no file is needed
for the standard local setup. To point at a different AI-service host/port, create
`frontend/.env.local` (gitignored):
```
NEXT_PUBLIC_API_BASE=http://localhost:7861
```

### c) CORS (only if needed)
The AI service allows all origins by default (`AI_CORS_ORIGINS` unset → `*`, no
cookies). To lock it to the frontend origin, add to root `.env`:
```
AI_CORS_ORIGINS=http://localhost:3000
```

## 3. Install dependencies

```bash
# Python (backend) — creates .venv from uv.lock
uv sync

# Frontend
cd frontend
npm install
cd ..
```

## 4. Run the servers (3 terminals)

Open three terminals at the repo root.

**Terminal 1 — Gradio graded app**
```bash
uv run python app.py
# → http://localhost:7860
```

**Terminal 2 — AI service (chat + voice + API)**
```bash
uv run uvicorn ai.main:app --port 7861
# → http://localhost:7861/health   ·   Swagger: http://localhost:7861/docs
```

**Terminal 3 — Next.js frontend**
```bash
cd frontend
npm run dev
# → http://localhost:3000
```

> On Windows the port is read from `PORT`; the `--port` flag above is enough.
> To change a port, e.g. `PORT=7862 uv run uvicorn ai.main:app --port 7862`.

## 5. Open the app

- **Customer web app:** <http://localhost:3000> — chat home, Menu (build a pizza),
  cart, checkout, orders, profile. (Best viewed narrow; on desktop it renders in a
  centered phone frame.)
- **Staff kiosk / Admin:** <http://localhost:3000/staff> · <http://localhost:3000/admin>
- **Graded Gradio app:** <http://localhost:7860>
- **AI API docs:** <http://localhost:7861/docs>

Quick smoke test (with `OPENROUTER_API_KEY` set):
```bash
curl -s http://localhost:7861/health
curl -s -X POST http://localhost:7861/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"what pizzas do you have?","session_id":null}'
```

---

## Tests & quality gates

```bash
uv run pytest                       # backend test suite
uv run pre-commit run --all-files   # isort / black / ruff / bandit
cd frontend && npx tsc --noEmit     # frontend typecheck
cd frontend && npm run build        # production build (stop `npm run dev` first — see below)
```

---

## Troubleshooting

- **Port already in use** — something is already bound to 7860/7861/3000. Stop it, or
  run on another port (`--port` for uvicorn, `PORT=xxxx` for Gradio, `npm run dev -- -p 3001`
  for the frontend, and update `NEXT_PUBLIC_API_BASE` accordingly).
- **Frontend loads but chat fails** — the AI service (7861) isn't running, or
  `OPENROUTER_API_KEY` is missing/invalid. Check `curl http://localhost:7861/health`.
- **`Cannot find module './###.js'` in the frontend** — a corrupted `.next` cache,
  usually from running `npm run build` while `npm run dev` was live. Fix:
  stop dev, delete `frontend/.next`, restart dev. **Never** build while dev is running.
- **Menu looks empty / "No updated menu saved yet"** — `database/menu_source.txt`
  points at a custom menu that isn't present. Set its contents back to
  `Use SliceMatic default menu` to use the bundled `menu_data/`.
- **Voice does nothing** — `DEEPGRAM_API_KEY` is unset; text chat still works.
