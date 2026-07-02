# CLAUDE.md — SliceMatic / PizzaFlow

Guidance for working in this repo. Read this before touching any code.

## What this is

FDE Academy applied project, **Group 3**. SliceMatic is a single-outlet pizza
delivery brand (New Ashok Nagar, Delhi). Built across three stages:

- **Stage 1 (done):** PRD + Business Unit Economics. See `docs/Stage1_PartA_PRD.md` and
  `docs/Stage1_PartB_BusinessEconomics.md`. Source of truth for business rules.
- **Stage 2 (done, deployed):** a working ordering app in Python — pure `core/` brain, a
  Gradio UI (`app.py`), a custom HTML/JS UI (`server.py` + `web/`), a shared FastAPI
  (`api/routes.py`), and a pytest suite. Deployed to Hugging Face Spaces via CI.
- **Stage 3 (current — building):** a **conversational AI ordering layer** (chat + browser
  voice) added **on top of the existing code without disturbing it**. This is the active work.

The graded brief is `reference/PizzaFlow_Assignment_Brief_FDE.pdf`. **When a rule here conflicts
with the brief or PRD, the brief/PRD win — fix this file.**

---

## ⏩ Stage 3 — current status & handoff (read this first)

Branch: **`feature/ai-conversational-layer`** (not pushed yet; sits on latest `master`).
Detailed checklist + decisions: `docs/STAGE3_PLAN.md`. API reference: `docs/API.md`.

**Synced with `master` (2026-06-30, PRs #11–#15):** UI rework + deployment config +
`database/` restructure. Key knock-ons the AI layer already adapts to:
- Order log is now `database/orders_log.txt` (`DATABASE_DIR` env); `core.persistence.append_order`
  returns `(timestamp, order_id)` and IDs are sequential `SM-000001`.
- Menu: bundled default `menu_data/` + admin-uploaded `database/menu/`; resolve via
  `api.routes._load_active_menu()` (honours `database/menu_source.txt`). The AI tools use it.
- A safety branch `backup/ai-pre-sync-20260630` exists if the merge ever needs auditing.

**Done (chat + voice backend complete, verified live):**
- `core/` unchanged; **`ai/`** layer added: `config`, `llm` (OpenRouter via OpenAI SDK +
  Langfuse auto-tracing drop-in), `session` (in-memory + Supabase mirror), `language` (en/hi),
  `tools` (6 in `_DISPATCH`, all calling `core/`; the LLM sees a **stage-gated subset** via
  `tools_for(session)`: get_customer_profile (hardcoded demo profile) + calculate_order_price
  (multi-topping lines, JSON result) + escalate_to_human always; confirm_and_save_order only
  after a priced, unsaved bill. get_menu/validate_customer exist but aren't exposed — the live
  menu is embedded in the system prompt each turn), `guardrails` (heuristics + cheap-LLM
  classifier, fail-open; deterministic output), `agent` (tool loop ≤5 rounds, app-level fallback,
  temp 0.2, OpenRouter reasoning disabled; **staged system prompt**: hard rules → output tags →
  few-shot examples from the live menu → fenced MENU → per-stage CURRENT STEP
  (building/payment/ordered/escalated, derived from session state); **UI injection**: bill JSON
  `[BILL]…[/BILL]` + `[PAYMENT_OPTIONS]` (chat) and the localized save confirmation (both
  channels) bypass the LLM), `deepgram` + `sarvam` (STT/TTS), `routers/chat.py` +
  `routers/voice.py`, `main.py` (FastAPI + CORS + /health). Chat/voice orders are **Supabase-only**
  (`db.orders.create_order`, no `.txt`); `[timing]` logs cover STT/TTS/LLM/agent.
- **`db/`** additive Supabase: `orders` mirror, `sessions`, `messages`, `escalations` — all best-effort
  with transient-retry (`db/client.execute_query`). `.txt` log stays primary.
- Supabase migrations **applied**: `0001_init_ai_schema.sql` (orders/sessions/messages),
  `0002_escalations.sql`, `0003_orders_user_and_number.sql` (adds `user_id`, DB-generated
  `order_no`, relaxes per-line NOT NULL for multi-item carts). Run new migrations manually in the
  SQL editor (no DDL via client).
- Dev tooling: pre-commit (isort/black/ruff/bandit), Claude PostToolUse hook, CI `lint` job.
- `postman/SliceMatic.postman_collection.json`, `docs/API.md`. **128 tests pass.**

**Run it** (full step-by-step for any human/LLM is in **`LOCAL_SETUP.md`** — 3 servers):
- AI service (chat/voice + `/api/*`): `uv run uvicorn ai.main:app --port 7861` (docs at `/docs`)
- Graded Gradio app (separate): `uv run python app.py` (port 7860)
- Frontend: `cd frontend && npm run dev` (port 3000) — needs the AI service running
- Tests/lint: `uv run pytest` · `uv run pre-commit run --all-files`

**Env:** `.env` (gitignored) holds the keys; `.env.example` is the template. Models:
`google/gemini-2.5-flash` + fallbacks `anthropic/claude-haiku-4.5`, `openai/gpt-4o-mini`.
Optional `LANGFUSE_PROJECT_ID` → clickable Langfuse links on escalations. `AI_CORS_ORIGINS`
for the Next.js origin.

**Step 6 — Next.js frontend: LARGELY BUILT** (in `frontend/`, see the "Stage-3 Frontend
architecture" section). Done: design system + configurable palettes (default **Signature**),
phone-frame demo presentation, customer **chat Home** (wired to `/chat`), **Menu** (2-per-row tiles →
inline build sheet: pizza→base→1–3 toppings→qty, live-priced), inline **cart**, dedicated
**checkout** (COD/Cash/UPI, simulated payment), **Orders** tab (simulated live tracking), **profile**
(hardcoded user), global cart icon. Additive backend endpoints added for it: `POST /api/cart/price`
and `POST /api/cart/checkout` (+ 14 tests). Design decisions were made with the **`ui-ux-pro-max`
skill** (installed via `uipro init --ai claude`, gitignored under `.claude/skills/`, regenerable).

**Next session — NOT done yet:**
1. **Voice UI**: built (`lib/use-voice.ts` + `components/chat/call-panel.tsx` — MediaRecorder,
   3-min countdown, TTS playback) but **DISABLED for this release** via `VOICE_ENABLED = false`
   in `components/chat/composer.tsx` (hides the call button/panel only; backend `/voice/*` and
   the hook are intact — flip the flag to re-enable, then polish/QA the call experience).
2. **Staff kiosk + Admin** surfaces are placeholder routes (`/staff`, `/admin`) — build them out.
3. **Step 7 — deploy**: HF `Dockerfile` runs `app.py` (Gradio) on 7860; decide how to ship
   `ai.main` + the Next.js app + update CI. Before any public deploy: **auth / rate-limiting** on
   `/chat` and `/voice/*` (none yet), and real order-status (Orders tracking is client-simulated).
4. Optional hardening: persist `tool`-role messages; rehydrate `history` on restart; **Redis** for
   sessions if running >1 worker/instance.

**Conventions for the AI layer:** keep `core/` free of web/DB/LLM imports; tools return plain
strings for the LLM and recompute money via `core/`; every Supabase call is best-effort (never
blocks an order); committed tests must run **without** keys/DB (lazy config + monkeypatching),
live checks go in throwaway scripts that clean up after themselves.

---

## The one rule that drives the architecture

The **grader swaps the three menu `.txt` files** before evaluating, runs the app, and
inspects `orders_log.txt`. If the app crashes on swapped/malformed files or bad input, we lose
marks. So:

- **`core/` is pure Python with NO web, DB, or LLM import.** Menu loading, validation, the
  pricing engine, and `orders_log.txt` persistence all live here and must run with nothing but
  the standard library (+ pandas for analytics) and the three `.txt` files present.
- **Every surface calls `core/` directly (in-process).** Gradio handlers, the FastAPI routes,
  and the new AI tool executor are all thin wrappers over the same `core/` functions.
- **FastAPI, the AI layer, and any DB are ADDITIVE.** The graded path must work even if they
  are absent. `orders_log.txt` is the primary, mandatory output; everything else mirrors it.

`uv run python app.py` must launch the full ordering flow with only the menu files present. Protect that.

---

## Hard business rules — do not paraphrase, implement exactly

These come from PRD §3–4 and the brief. They are graded literally. They are already implemented
in `core/` — the AI layer must reuse them, never reimplement them.

### Validation (`core/validation.py`)
| Field | Rule | Reject examples |
|---|---|---|
| Name | Alphabets + spaces only, 2–40 chars, not blank/whitespace-only | `"   "`, `"A"`, digits, symbols |
| Phone | Exactly 10 digits, first digit ∈ {6,7,8,9} | `1234567890`, 9-digit, letters |
| Quantity | Integer 1–10 only | `0`, `11`, `-1`, `2.5`, `"three"`, empty |
| Menu selection | Valid list number, in range | `0`, > menu length, letters, empty, a price typed as the number |
| Payment | Exactly one of 1=Cash, 2=Card, 3=UPI | anything else |

Every validator returns `(ok, value_or_message)`. On failure the message says what was wrong and
what is expected (NFR-2). Nothing raises on bad input — callers re-prompt with the message.

### The 8 edge cases that WILL be tested (all must not crash)
1. Name with only spaces ·
2. Phone 10 digits starting with 1 ·
3. Quantity 0 and 11 ·
4. Selection 0 or > menu length ·
5. A price number typed instead of an item number ·
6. Empty input at every prompt ·
7. Non-integer quantity (`three`, `2.5`) ·
8. Menu file with a missing price field.

### Pricing engine (`core/pricing.py`) — compute in EXACTLY this order, round money to 2 dp, INR
```
unit_price = base_price + pizza_price + topping_price
subtotal   = unit_price * quantity
discount   = 0.10 * subtotal   if quantity >= 5   else 0
taxable    = subtotal - discount
gst        = 0.18 * taxable            # 18% on POST-discount amount
total      = taxable + gst
```
**Regression test (must pass exactly):** Cheese Burst ₹229 + BBQ Chicken ₹379 + Extra Cheese ₹69
= ₹677 unit; qty 5 → subtotal ₹3385 → discount ₹338.50 → taxable ₹3046.50 → GST ₹548.37 →
**total ₹3594.87**. The LLM/agent must NEVER compute money — only this engine does.

### Defensive menu parsing (`core/menu.py` — the grader swaps files)
Each line is `ID;Name;Price`. Strip whitespace, tolerate blank lines, validate price is numeric,
skip lines with missing fields, ignore duplicate IDs, handle a varying number of items per file.
Missing/unreadable file or an empty category → `MenuError` (clear message, graceful), **no stack trace**.

### orders_log.txt format (`core/persistence.py` — parseable, graded)
One order per block, **pipe-separated** fields within a line, a **blank line between orders**.
Stable field order (NFR-4):
```
timestamp | name | phone | base | pizza | topping | unit_price | quantity | subtotal | discount | gst | total | payment_mode
```
Append on every completed order. Money values rounded to 2 dp. On Hugging Face the log is written
to `/data/orders_log.txt` (persistent volume); locally to `./orders_log.txt`.

---

## Actual architecture & module map (what exists today)

> The Stage-3 plan below originally referenced `core/orders.py` and `core/menu_loader.py`.
> **Those names do not exist.** Use the real names and signatures here.

```
core/                # pure Python (stdlib + pandas) — the graded brain. NO gradio/fastapi/LLM/DB here.
  models.py          #   frozen dataclasses: MenuItem(id,name,price), Menu(bases,pizzas,toppings), Bill(...)
  menu.py            #   load_menu(menu_dir="menu_data") -> Menu;  raises MenuError. parse_menu_lines(),
                     #   load_category(). Defaults: Types_of_Base/Pizza/Toppings.txt
  validation.py      #   validate_name / validate_phone / validate_quantity / validate_selection /
                     #   validate_payment  -> (ok, value|error_msg). PAYMENT_MODES = {1:Cash,2:Card,3:UPI}
  pricing.py         #   compute_bill(base, pizza, topping, quantity) -> Bill   (the engine above)
                     #   get_discount_rate() / set_discount_rate(rate)  (runtime-adjustable discount)
  persistence.py     #   append_order(*, name, phone, bill, payment_mode, timestamp=None, path=LOG_FILE) -> ts
                     #   format_order_line(...); FIELD_ORDER; LOG_FILE (/data on HF)
  analytics.py       #   load_orders_df() + get_analytics(filter_type) -> dict of pandas frames/totals
api/
  routes.py          #   FastAPI APIRouter(prefix="/api"): /health /menu /validate/customer /summary
                     #   /order /config (get+set discount) /analytics. Thin wrappers over core/.
app.py               #   Gradio Blocks UI mounted on FastAPI (single process). Calls core/ directly.
server.py            #   FastAPI serving the custom web/ frontend + the same api/routes. Port 7861 local.
web/                 #   vanilla HTML/JS/CSS frontend (index.html, app.js, style.css) → calls /api/*
menu_data/           #   the three default .txt files. Grader swaps these.
tests/               #   pytest: pricing regression, all 8 edge cases, log format, defensive parsing
orders_log.txt       #   generated; a sample is committed for submission
Dockerfile           #   Hugging Face Spaces (sdk: docker, app_port 7860)
```

### Key real signatures the AI tool layer must call (do not rename/adapt)
- **Menu:** `menu.load_menu(menu_dir) -> Menu`; then `Menu.bases / .pizzas / .toppings`, each a
  list of `MenuItem`. Resolve an item by id with a helper like `next(i for i in items if i.id == _id)`
  (see `api/routes._find` / `_resolve`).
- **Pricing:** `pricing.compute_bill(base, pizza, topping, quantity) -> Bill` — takes **resolved
  `MenuItem` objects for ONE configuration**, not a list of order lines and not raw IDs. To bill a
  multi-line order you loop `compute_bill` per line and sum the `Bill.total`s yourself (no existing
  function does multi-line totalling — add it in the wrapper, not in `core/pricing`).
- **Persistence:** `persistence.append_order(name=, phone=, bill=, payment_mode=) -> timestamp`
  writes `orders_log.txt`. **This is the only order-saving function that exists today.**

### Process model & API wiring (DECIDED — do not re-litigate)
**One process per surface, single source of truth = `core/`.** Handlers call `core/` in-process,
never over HTTP. FastAPI (`api/routes.py`) exposes the same `core/` functions for `/docs`, the
custom frontend, and external callers; the UIs do not depend on a running API for the graded path.
Do NOT make a UI call its own endpoints via `requests`/HTTP.

---

## Stage 3 — Conversational AI ordering layer (ADDITIVE; the current work)

A conversational ordering experience on the website, in **two channels**:
- **Chat** — text conversation.
- **Voice** — browser mic, AI speaks back (WebRTC/MediaRecorder, **no telephony**).

The AI takes the order, reads the bill back, waits for confirmation, then saves. **It never
computes prices and never invents menu items** — it only orchestrates `core/`.

### The cardinal rule, mapped to the real code
- **Read every file in `core/` before writing anything.** It is tested and works.
- The AI layer's tool executor is the **only** new code that touches `core/`, and it does so by
  **importing and calling the real functions** (`menu.load_menu`, `pricing.compute_bill`,
  `persistence.append_order`, `validation.*`) — same brain as the existing UIs, no HTTP between them.
- Pricing → `core/pricing.py`. Order saving → `core/persistence.append_order` (and optionally a
  parallel DB write, see Supabase note). Menu → `core/menu.py`. Validation → `core/validation.py`.

### Proposed package layout (avoid the `app.py` name clash)
The original plan put everything under `app/`, which collides with the existing `app.py` Gradio
entrypoint. **Use a distinct package** for the AI layer:
```
ai/                          ← NEW conversational layer (additive)
  main.py                    ← FastAPI entrypoint (or mount onto existing server.py)
  config.py                  ← env settings; fail fast if a required var is missing
  session.py                 ← per-conversation in-memory state (note where Redis would replace it)
  language.py                ← English / Hindi detection
  guardrails.py              ← input + output validation (output reuses core/validation.py)
  tools.py                   ← LLM tool schemas (TOOL_DEFINITIONS) + execute_tool(); imports core/
  agent.py                   ← system-prompt builder, OpenRouter caller, tool loop, fallback chain
  observability.py           ← Langfuse trace wrapper (never breaks the main flow)
  routers/
    chat.py                  ← POST /chat
    voice.py                 ← POST /voice/transcribe, /voice/respond, /voice/synthesize
frontend (Stage-3 UI)        ← see "Frontend" below — choice still open (Next.js vs reuse web/)
```
Keep `core/` clean of LLM/DB imports — all third-party AI/DB SDKs live under `ai/`.

### Tech stack (Stage 3)
| Concern | Choice |
|---|---|
| Backend | FastAPI (Python) — reuse/extend the existing app |
| LLM | OpenRouter — tool-use / function calling |
| STT | Deepgram Nova-2 (`language=multi` for bilingual) |
| TTS | Deepgram Aura (English). Hindi TTS = Phase 2 swap (Google Cloud / Azure) — mark the seam |
| Observability | Langfuse free tier |
| Database | **OPEN** — Supabase (Postgres) is planned, but no core save function exists yet (see note) |
| Frontend | **DECIDED — Next.js 15** (App Router, TS, Tailwind v4, shadcn-style primitives). See "Stage-3 Frontend" below. |

> **Database is still OPEN** (Supabase vs sticking to `orders_log.txt`) — pick before building
> that layer; the chat/voice/agent work doesn't depend on it. **Frontend is now decided: Next.js**
> lives in `frontend/` — full conventions in the **Stage-3 Frontend architecture** section below.

### Stage-3 Frontend architecture (`frontend/` — Next.js 15) — READ before touching the UI

The web UI lives in **`frontend/`** (its own npm project; do NOT confuse with the graded Python
`web/`/`app.py`). Stack: **Next.js 15 App Router + TypeScript + Tailwind v4 + shadcn-style
primitives + Zustand + Framer Motion**, talking to the AI service over HTTP via
`NEXT_PUBLIC_API_BASE` (default `http://localhost:7861`). It is **additive** — the graded Python
path never depends on it.

> We use **Next.js 15 (stable)**, not 16. `create-next-app` scaffolds 16 by default; we downgraded
> for stability and **deleted its auto-generated `frontend/AGENTS.md` + `frontend/CLAUDE.md`**
> (they described Next-16 behavior and injected agent "hints"). Do not reintroduce them.

**The two load-bearing decisions (keep these invariants):**

1. **Three independent surfaces, isolated by route group.** `app/(customer)/`, `app/(staff)/`,
   and `app/(admin)/` each own their **own `layout.tsx`** (own nav/providers) and their own
   feature code under `components/{customer,staff,admin}/`. They share **nothing** but the root
   `app/layout.tsx` (fonts + `ThemeProvider`). Rationale: a teammate/LLM can build or change one
   surface (e.g. admin) without importing from — or being able to break — the others. **Never make
   one surface import another surface's components or layout.** **Auth + role-based access is a
   FUTURE plan** — today each surface is a plain unguarded route (`/`, `/staff`, `/admin`) reached
   by URL. When auth lands, the role gate goes in each group's `layout.tsx` (the seam is already
   there); the correct screen is chosen by the signed-in user's role.

2. **Configurable palettes via semantic CSS vars only.** All colors are semantic CSS variables in
   `app/globals.css`, defined per palette under `[data-theme="..."]`; `lib/themes.ts` is the
   registry and `components/theme-provider.tsx` swaps `<html data-theme>` (persisted to
   localStorage). Components read tokens (`bg-primary`, `text-muted-foreground`, …) — **never a
   raw hex**. Add a palette = one CSS block + one `THEMES` entry; everything else picks it up.

   **Default = `brand` ("Signature") — the locked house palette. DO NOT deviate without asking.**
   Five colors + tints only, **no pure white/black**: ink `#19181A` (dominant surface → `background`),
   sage `#479761` (the ONE dominant accent/CTA → `primary`/`ring`/`success`/user bubble), sand
   `#CEBC81` (sparing secondary/pay → `secondary`+`accent`), plum `#A16E83` (rare emphasis →
   `destructive`; the palette has no red), stone `#B19F9E` (muted text/dividers → `muted-foreground`),
   warm off-white `#EDE8E2` (`foreground`). Rules: ink dominates every surface; only one accent
   visually dominant per screen (sage) — don't mix sage/sand/plum at equal weight; AA contrast (light
   text on ink, dark ink text on sage/sand/stone). `midnight`/`classic`/`basil` remain as alt themes.

**Shared vs. isolated (the seam that prevents cross-breakage):**
- **Shared + stable:** `components/ui/` (Button, Card, Input, Badge — the design system) and
  `lib/api.ts` (typed client). These are **additive-only**: add functions/variants, don't rewrite
  existing ones. `lib/utils.ts` has `cn()` + `formatINR()`.
- **Isolated per surface:** screens, feature components, and state stores (`lib/store.ts` is the
  customer chat store; a future admin store is its own slice).

**Customer UX flow (decided — honor exactly):** Home = a live **chat thread** (greeting +
quick-reply chips + text/mic composer), voice is an **input modality into the same `/chat`
pipeline** (not a separate mode); a separate **Menu** tab for browse/search with an **inline**
customization sheet and **inline** cart sheet (no navigation); **only checkout** breaks the inline
pattern to a dedicated `/checkout` route; after payment → **Orders** tab for tracking.
**Demo framing (device idiom by role):** the customer app is phone-first — on desktop it renders in a
**centered phone-width frame** (`max-w-md` column, `bg-backdrop` gutters, borders/shadow; `sm:`
breakpoint), full-screen on real phones. Staff (kiosk) + admin (dashboard) are desktop-wide. This lets
the grader see the true mobile user flow on any screen. Bottom sheets are `max-w-md` so they align with
the frame. Header is centered (brand middle, cart + profile avatar right). The Next.js dev "N" indicator
is disabled (`devIndicators: false`).

**Staff** = kiosk POS (no chat/voice). **Admin** = not yet scoped. **Checkout stays a dedicated
`/checkout` route, NOT inline** (money + sensitive data — deliberate). The **global header** carries
a cart icon (opens the cart sheet from any screen via `menu-store.cartOpen`) + a profile avatar →
`/profile`. **User is hardcoded** in `lib/user.ts` (`CURRENT_USER`) until auth lands; it prefills
checkout. The palette switcher lives on `/profile` under "Appearance".

**Money & menu rules still apply to the UI:** never compute prices client-side — only offer items
from `/api/menu`, and price/place via the API. **Additive multi-topping cart endpoints** (in
`api/routes.py`, `core` untouched): `POST /api/cart/price` and `POST /api/cart/checkout` accept
lines of `{base_id, pizza_id, topping_ids[1..3], quantity}`; the server fuses the 1–3 toppings into
one combined topping (summing menu prices) and calls the frozen `core.compute_bill`.
`payment_mode`: COD & Cash both → `Cash` ("1"), UPI → `UPI` ("3") — only Cash/Card/UPI are valid;
Card is unused. Payment is **simulated** (no gateway; UPI shows a fake processing step).

> **DB is the source of truth for API-placed orders (DECIDED).** `POST /api/cart/checkout` writes to
> **Supabase ONLY, not `orders_log.txt`** — one order row per cart (line breakdown in `items` jsonb),
> stamped with **`user_id`** (hardcoded `CURRENT_USER.id` now; real auth later — list orders by user).
> `order_no` is **generated by the DB** (`SM-YYYYMMDD-NNNN`, migration `0003`), not the `.txt`
> counter. The DB write **raises/surfaces on failure** (no `.txt` fallback for API orders). Read via
> **`GET /api/orders?phone=`** (interim per-user filter until real auth; `?user_id=` also supported —
> swap back later); the Orders tab loads by `CURRENT_USER.phone` (`lib/orders-store.ts`, DB-backed)
> with a **simulated** status stepper from `created_at`. **The graded Gradio app is unaffected — it
> still writes `orders_log.txt` via `core.persistence`.** The AI `confirm_and_save_order` tool is
> **also DB-only now** (same `db.orders.create_order` path: one row per order, `items` jsonb,
> `source` chat|voice, `user_id` from the hardcoded profile; DB failure is surfaced to the LLM, order
> NOT placed). Only the single-line `/api/order` (vanilla `web/`) still writes `.txt` + mirror. **Gaps:** no promo-code or size fields (base = crust); voice
> MediaRecorder wiring is a later milestone. Checkout hides the bottom tab bar (dedicated screen).

**Run:** `cd frontend && npm run dev` (port 3000). Set `AI_CORS_ORIGINS=http://localhost:3000` in
the root `.env` so the AI service accepts browser calls.

### Environment variables (`.env`, loaded by `ai/config.py`)
```
OPENROUTER_API_KEY
DEEPGRAM_API_KEY
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
LANGFUSE_HOST
PRIMARY_MODEL        = google/gemini-2.5-flash
FALLBACK_MODEL_1     = anthropic/claude-haiku-4.5
FALLBACK_MODEL_2     = openai/gpt-4o-mini
# Only if Supabase is adopted:
SUPABASE_URL
SUPABASE_SERVICE_KEY
```
Keep secrets out of git.

### LLM tools (`ai/tools.py`) — schemas + executor, each calling real `core/` functions
Define each as an OpenAI-compatible function schema (OpenRouter accepts the same format).

- **`get_menu`** — no params. Calls `menu.load_menu(MENU_DIR)`; returns bases/pizzas/toppings with
  IDs and prices for the LLM to read. (Mirror of `GET /api/menu`.)
- **`calculate_order_price`** — params: order lines, each `{base_id, pizza_id, topping_id, quantity}`.
  For each line: validate quantity via `validation.validate_quantity`, resolve IDs to `MenuItem`s
  from the loaded `Menu`, call `pricing.compute_bill(...)`; sum totals across lines. Return a
  human-readable bill string and **store the resulting Bill(s) on the session** for `confirm_and_save`.
  (Mirror of `POST /api/summary`, which today handles a single line — multi-line summation is new wrapper logic.)
- **`confirm_and_save_order`** — called only after the customer confirms. Run the **output guardrail**
  first (reuse `core/validation` for name/phone/qty + menu-existence check). If valid, call
  `persistence.append_order(name=, phone=, bill=, payment_mode=)` (and the DB mirror if adopted).
  Return a success message with the order number/timestamp. (Mirror of `POST /api/order`.)
- **`escalate_to_human`** — param: reason. Sets `human_escalated` on the session; returns a relay message.

### Session state (`ai/session.py`, in-memory, one per session_id)
Tracks: `session_id`, `order_source` (chat|voice), `language` (en|hi), conversation history
(role/content dicts), extracted fields (name, phone, items), pricing result, `confirmed`,
`human_escalated`, `voice_start_time` (3-minute cap). Session IDs come from the frontend; create
one if absent. In-memory is fine for the demo — note where Redis would replace it.

### Language handling (`ai/language.py`)
Detect per turn (customer may switch). Devanagari script → Hindi; common Hinglish words → Hindi;
else English. Store on session; pass to the system prompt so the LLM replies in kind. Hindi voice
TTS is the marked Phase-2 swap.

### Guardrails (`ai/guardrails.py`)
- **Input (before the LLM):** block + politely redirect on prompt injection, abuse, or clearly
  off-topic long messages. Short messages/greetings always pass — do not over-filter.
- **Output (inside `confirm_and_save_order`, before any write):** reuse `core/validation` — name
  2–40 letters/spaces, phone 10-digit 6–9 start, every item's IDs exist in the live menu, qty 1–10,
  ≥1 item. On failure, return errors to the LLM to re-prompt; **never write on failure**.

### Agent loop (`ai/agent.py`)
Per turn: build messages (system prompt + history) → call OpenRouter with tool defs → if tool calls,
execute each, append results, loop → if plain text, return it. **Cap at 5 tool-call rounds.**
**Fallback chain:** PRIMARY → FALLBACK_1 → FALLBACK_2 on any error/timeout/rate-limit; if all fail,
apologize politely in the detected language. Log which model was used to Langfuse each turn.
System prompt includes: restaurant persona, language instruction, the full live menu (from
`menu.load_menu`, never hardcoded), required fields, the never-compute/never-invent/confirm-first
rules, and a "speak naturally, no markdown" note for voice.

### Voice pipeline (`ai/routers/voice.py` + frontend)
- `POST /voice/transcribe` — audio blob + session_id; enforce 3-min cap via `voice_start_time`
  (`call_ended: true` when exceeded); Deepgram Nova-2 `language=multi`; return transcript.
- `POST /voice/respond` — transcript + session_id; input guardrail → agent loop → text reply.
- `POST /voice/synthesize` — text + language; Deepgram Aura (English); **mark the Hindi-TTS swap point**.
- Browser: MediaRecorder (`audio/webm;codecs=opus`), click-to-start/stop, disable mic while
  processing, 3:00 countdown, stop on `call_ended`, play TTS audio.

### Supabase note (the real gap)
The draft assumed a `core/orders.py` that saves to Supabase. **It does not exist.** Today the only
persistence is `core/persistence.append_order` → `orders_log.txt`. If Supabase is adopted, add the
DB write as an **additive parallel mirror** (its own module under `ai/` or a new `db/` package) —
**do not** put a DB import in `core/`, and keep `orders_log.txt` as the primary, graded output.
Proposed `orders` table (if adopted): id (uuid pk), created_at, customer_name, customer_phone,
items (jsonb), subtotal, discount_percent, discount_amount, gst_percent (18), gst_amount,
total_payable, order_source (chat|voice), language_detected (en|hi), session_id,
human_escalated (bool), status (received|confirmed|cancelled); index created_at desc + order_source.

### Observability (`ai/observability.py`)
Wrap every LLM call in a Langfuse trace: session_id, model used, input messages, output, tool
calls, token counts. Wrap in try/except — **observability errors must never reach the customer**.

### Stage-3 build order
1. Read all of `core/` and `api/routes.py` — confirm real signatures.
2. Decide frontend + DB (the two open items above).
3. `ai/config.py` → `ai/session.py` → `ai/language.py` → `ai/guardrails.py` →
   `ai/tools.py` → `ai/observability.py` → `ai/agent.py` → `ai/routers/chat.py` →
   `ai/routers/voice.py` → wire into FastAPI (extend `server.py` or `ai/main.py`) → frontend.
4. Manual test via the demo checklist.

### Stage-3 demo checklist
- qty 4 → no discount; qty 5 → 10% discount · item not on menu → polite redirect ·
- prompt injection → blocked · abusive text → redirected · kill PRIMARY key → fallback fires ·
- Hindi in → Hindi out · English in → English out · voice > 3 min → graceful cap ·
- "speak to a human" → escalation · cancel mid-order → session resets ·
- confirm order → **graded Gradio app** writes `orders_log.txt`; **API/frontend checkout AND the AI
  chat/voice tool** write the **Supabase `orders`** row (DB-only, `user_id`, `items` jsonb) — all
  with correct core pricing. Orders tab lists them by the profile phone.

---

## Conventions
- **Tooling is `uv`** (uv 0.11, Python ≥3.12). Manage deps in `pyproject.toml` via `uv add`;
  run with `uv run` (`uv run python app.py`, `uv run pytest`, `uv run python server.py`).
  `uv.lock` is committed. `requirements.txt` is generated for the Hugging Face Space.
- Currency is INR everywhere; round money to 2 dp at display and in the log.
- Don't hardcode menu items or prices — everything comes from the `.txt` files at runtime.
- `node_modules/` belongs to the `ppt/` slide generator; ignore it for app work.

## Deployment & CI/CD
- **Target:** Hugging Face Spaces (Docker SDK, `app_port` 7860). `orders_log.txt` persists at `/data`.
- **PR Checks** (`.github/workflows/pr-checks.yml`): on PRs to `master`, installs deps and runs
  `pytest`. Failing tests block merge.
- **Sync to HF** (`.github/workflows/sync-to-hf.yml`): on merge to `master`, pushes to the Space via
  the `hf` CLI, excluding large binaries (`.pdf`, `.pptx`); the Space rebuilds the Docker container.

## Don't
- Don't put gradio / fastapi / LLM / DB imports in `core/`.
- Don't let the AI layer, FastAPI, or a DB become a hard dependency of the graded flow.
- Don't compute prices anywhere except `core/pricing.py`. Don't let the LLM compute money.
- Don't invent menu items — the LLM may only offer items from the live menu.
- Don't write to any store before the output guardrail passes AND the customer confirms.
- Don't change the validation rules, pricing order, or log field order without checking the PRD/brief.
- Don't let any input crash the app — every prompt validates and re-prompts.
- Don't use external telephony (Twilio/Exotel) — voice is browser-only.
- Don't let observability errors surface to the customer.

## Future Architecture Note: UI Injection
Currently, deterministic outputs (like the order bill) are passed through the LLM as strings to be wrapped in tags (e.g., `[BILL]...[/BILL]`). While this ensures context awareness, it introduces token-generation latency.
A hyper-optimized future architecture should use **UI Injection**: The backend tool would instantly push the UI component to the frontend via a side-channel, and simply return a system note to the LLM (e.g., *'Bill shown to user, proceed to payment'*). This bypasses the LLM for rendering deterministic data, resulting in zero latency for the receipt and absolute determinism.
