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
| Frontend | **OPEN** — Next.js (per stack table) vs reuse the existing vanilla `web/` single-file UI |

> **Two decisions are unresolved** and were left as-is from the draft: the **frontend framework**
> (Next.js vs the existing vanilla `web/`) and the **database** (Supabase vs sticking to
> `orders_log.txt`). Pick these before building those layers; the chat/voice/agent work doesn't
> depend on either.

### Environment variables (`.env`, loaded by `ai/config.py`)
```
OPENROUTER_API_KEY
DEEPGRAM_API_KEY
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
LANGFUSE_HOST
PRIMARY_MODEL        = google/gemini-2.0-flash-exp
FALLBACK_MODEL_1     = anthropic/claude-haiku-3-5
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
- confirm order → appears in `orders_log.txt` (and Supabase if adopted) with correct pricing.

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
