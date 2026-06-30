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
### 5. AI layer (`ai/` package) — chat first, voice after. Each sub-step is tested before the next.
- [ ] **5.1** Deps (`openai` for OpenRouter, `langfuse`) + `ai/config.py` — load `.env`, fail
      fast on missing required vars. _Verify: import config, settings populated._
- [ ] **5.2** `db/sessions.py` + `db/messages.py` — best-effort writes (same pattern as
      `db/orders.py`). _Verify: live insert/read-back/cleanup._
- [ ] **5.3** `ai/session.py` (in-memory store, mirrors to `sessions`) + `ai/language.py`
      (en/hi detection). _Verify: unit tests._
- [ ] **5.4** `ai/tools.py` — 4 tool schemas + `execute_tool()` calling `core/`
      (get_menu, calculate_order_price, confirm_and_save_order, escalate_to_human).
      _Verify: unit-test each tool against the default menu, no LLM._
- [ ] **5.5** `ai/guardrails.py` — input (pre-LLM injection/abuse/off-topic) + output
      (reuse `core.validation` + menu existence). _Verify: unit tests._
- [x] **5.6** `ai/observability.py` (Langfuse auto-tracing drop-in) + `ai/agent.py` (OpenRouter
      tool loop, cap 5 rounds, app-level fallback chain, warm persona @ temp 0.5). Verified live:
      2-turn order placed end-to-end; fallback chain proven; model IDs fixed to valid OpenRouter ids.
- [x] **5.6b** Escalations: `supabase/migrations/0002_escalations.sql` + `db/escalations.py`;
      `escalate_to_human` records a row with a summary `reason`, customer snapshot, and Langfuse
      links (transcript via messages, trace via langfuse_url/session_id). Verified live.
- [x] **5.7** `ai/routers/chat.py` (POST /chat: guardrail → agent → persist messages, per-session
      lock) + `ai/main.py` (FastAPI app incl. `api/routes` + CORS for Next.js + /health).
      Verified: committed tests (health/blocked/session) + live HTTP order via TestClient → DB.
- [ ] **5.8** Voice — Deepgram STT/TTS + `ai/routers/voice.py`
      (`/voice/transcribe|respond|synthesize`). _Verify: audio sample / mock._

- [ ] **6. Frontend** — Next.js (DECIDED), chat + voice panels, calls the FastAPI endpoints.
- [ ] **7. Wire + deploy** — Dockerfile/CI for the AI service; demo checklist.

## Decisions
- Architecture: logic stays in `core/`; AI layer orchestrates via tools; FastAPI endpoints feed Next.js.
- Supabase via `supabase-py`; menu still loads from text files; `.txt` log stays primary.
- Frontend: **Next.js**.

## Open
- Whether multi-line orders (cart of several pizzas) are in scope for the demo, or single-config only.
