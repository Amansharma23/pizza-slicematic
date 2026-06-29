# Stage 3 — Conversational AI Layer: Build Plan

Branch: `feature/ai-conversational-layer`. Additive only — the graded Stage-2 path
(`app.py` → `core/` → `orders_log.txt`) must keep working untouched.

## Principles
- Menu, pricing, validation, and the `.txt` log stay in pure `core/` (no DB/LLM imports).
- The LLM never computes money or invents items — it only calls `core/` via tool wrappers.
- Supabase is an **additive parallel write**; a Supabase failure must never break the `.txt` log.
- Supabase access = `supabase-py` REST client (not SQLAlchemy).

## Steps

- [x] **1. Schema** — `supabase/migrations/0001_init_ai_schema.sql`: `orders`, `sessions`, `messages`.
- [x] **2. Provision** — Supabase project live; migration run; creds in `.env`.
- [x] **3. DB package** — `supabase` + `python-dotenv` added; `db/client.py` (lazy singleton) +
      `db/orders.py` done. `db/sessions.py` + `db/messages.py` deferred to Step 5 (AI layer uses them).
- [x] **4. Dual write** — after `core.persistence.append_order(...)`, best-effort mirror into the
      `orders` table. Wired (guarded import) into `app.py` `pay()` (source=`gradio`) +
      `api/routes.place_order` (source=`api`). `core/` stays DB-free. Verified live; 60 tests pass.
- [ ] **5. AI layer** (`ai/` package):
      - `config.py` — load `.env`, fail fast on missing required vars
      - `session.py` — in-memory session store (mirrored to `sessions` table)
      - `tools.py` — 4 tools → real `core/` fns (get_menu, calculate_order_price,
        confirm_and_save_order, escalate_to_human)
      - `agent.py` — OpenRouter tool loop + fallback chain (primary → 2 fallbacks)
      - `guardrails.py` — input (pre-LLM) + output (reuse `core.validation`)
      - `observability.py` — Langfuse trace wrapper (never breaks main flow)
      - `routers/chat.py` — `POST /chat`
      - `routers/voice.py` — `POST /voice/transcribe|respond|synthesize` (Deepgram)
- [ ] **6. Frontend** — OPEN decision: Next.js vs vanilla single-file. Chat + voice panels.
- [ ] **7. Wire + deploy** — mount AI routers into the FastAPI app; update Dockerfile/CI; demo checklist.

## Open decisions
- Frontend framework (Next.js vs vanilla).
- Whether multi-line orders (cart of several pizzas) are in scope for the demo, or single-config only.
