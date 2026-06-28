# CLAUDE.md — SliceMatic / PizzaFlow

Guidance for working in this repo. Read this before touching MVP code.

## What this is

FDE Academy applied project, **Group 3**. SliceMatic is a single-outlet pizza
delivery brand (New Ashok Nagar, Delhi). We are building its ordering system across 3 stages:

- **Stage 1 (done):** PRD + Business Unit Economics. See `docs/Stage1_PartA_PRD.md` and
  `docs/Stage1_PartB_BusinessEconomics.md`. These are the source of truth for business rules.
- **Stage 2 (current — MVP):** a working Gradio ordering app in Python. Due **Jun 27**, 30 pts.
- **Stage 3 (next):** full-stack rebuild (Vercel + Supabase + OpenRouter AI feature). Due Jul 2.

The graded brief is `reference/PizzaFlow_Assignment_Brief_FDE.pdf`. **When a rule here conflicts
with the brief or PRD, the brief/PRD win — fix this file.**

## The one rule that drives the architecture

The **grader swaps the three menu `.txt` files** before evaluating, runs the Gradio app, and
inspects `orders_log.txt`. If the app crashes on swapped/malformed files or bad input, we lose
marks. So:

- **`core/` is pure Python with NO web or DB import.** Menu loading, validation, the pricing
  engine, and `orders_log.txt` persistence all live here and must run with nothing but the
  standard library + the three `.txt` files present.
- **Gradio (`app.py`) calls `core/` directly.** It does not depend on a running FastAPI server.
- **FastAPI and SQLite/SQLAlchemy are ADDITIVE.** They wrap the same `core/` functions. The
  graded path must work even if they are absent. SQLite is a *parallel* write; the `.txt` log is
  primary and mandatory.

`python app.py` must launch the full ordering flow with only the menu files present. Protect that.

## Hard business rules — do not paraphrase, implement exactly

These come from PRD §3–4 and the brief. They are graded literally.

### Validation
| Field | Rule | Reject examples |
|---|---|---|
| Name | Alphabets + spaces only, 2–40 chars, not blank/whitespace-only | `"   "`, `"A"`, digits, symbols |
| Phone | Exactly 10 digits, first digit ∈ {6,7,8,9} | `1234567890`, 9-digit, letters |
| Quantity | Integer 1–10 only | `0`, `11`, `-1`, `2.5`, `"three"`, empty |
| Menu selection | Valid list number, in range | `0`, > menu length, letters, empty, a price typed as the number |
| Payment | Exactly one of 1=Cash, 2=Card, 3=UPI | anything else |

Every rejection gives a **specific** message (what was wrong + what's expected) and re-prompts.
Never a generic error, never a crash, never an unhandled exception. (NFR-2)

### The 8 edge cases that WILL be tested (all must not crash)
1. Name with only spaces · 
2. Phone 10 digits starting with 1 · 
3. Quantity 0 and 11 ·
4. Selection 0 or > menu length · 
5. A price number typed instead of an item number ·
6. Empty input at every prompt · 
7. Non-integer quantity (`three`, `2.5`) ·
8. Menu file with a missing price field.

### Pricing engine — compute in EXACTLY this order, round money to 2 dp, INR on every line
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
**total ₹3594.87**. The LLM/agent (Stage 3) must NEVER compute money — only this engine does.

### Defensive menu parsing (the grader swaps files)
Each line is `ID;Name;Price`. Strip whitespace, tolerate blank lines, validate price is numeric,
skip/handle lines with missing fields, handle a varying number of items per file. Missing or
malformed file → clear error + graceful exit, **no stack trace**. (NFR-5/6, edge case 8)

### orders_log.txt format (parseable — graded)
One order per block, **pipe-separated** fields within a line, a **blank line between orders**.
Stable field order (NFR-4):
```
timestamp | name | phone | base | pizza | topping | unit_price | quantity | subtotal | discount | gst | total | payment_mode
```
Append on every completed order. Money values rounded to 2 dp, INR.

## Architecture (target)

```
core/            # pure Python, stdlib only — the graded brain. No gradio/fastapi/sqlalchemy here.
  menu.py        #   defensive loader: parse ID;Name;Price, skip bad lines, graceful errors
  validation.py  #   name / phone / quantity / selection / payment validators -> (ok, value|error_msg)
  pricing.py     #   the pricing engine above; deterministic; unit-tested against the worked example
  persistence.py #   append_order() -> orders_log.txt in the exact pipe format
  models.py      #   plain dataclasses (Order, Customer, BillLine) — no ORM
app.py           # Gradio Blocks, state-driven, 4 screens. Calls core/. The graded entry point.
api/             # ADDITIVE: FastAPI reusing core/ (/menu, /customer, /summary, /order, /payment)
db/              # ADDITIVE: SQLAlchemy models + SQLite; parallel writes to users + orders tables
menu_data/       # the three .txt files (default menu). Grader swaps these.
tests/           # pytest: pricing regression, all 8 edge cases, log format, defensive parsing
orders_log.txt   # generated; a sample committed for the Stage 2 submission
```

### Order status state machine (our enhancement — funnel tracking, not required by the brief)
`started → menu_selected → payment_selected → payment_in_progress → ordered | failed`
Captured per screen so we can show drop-off. This is extra; it must never break the graded path.

### Two SQLite tables (additive, Stage-3 forward-looking)
- `users` — dedup by phone; name, phone, first/last seen. Powers Stage 3 Option A (recommend from
  past orders).
- `orders` — full bill fields + payment_mode + status + order_no + timestamps + source.

The `.txt` files (menu in, `orders_log.txt` out) remain the mandatory, primary I/O. SQLite mirrors.

## Gradio UI rules (from the brief)
- A **sequence of steps**, not one giant form. `gr.Blocks` + `gr.State` driven.
- The bill MUST render in `gr.Dataframe` or `gr.HTML` — **never a plain text box**.
- Re-prompts keep the user in context; specific error messages inline.
- Stage 2 is graded on **correctness and robustness, not aesthetics** — get the core bulletproof
  first, then polish for the Hugging Face demo.

### The 4 screens (our flow)
1. **Launch / menu** — proceed with the bundled default menu, or upload your own 3 files. Uploading
   requires all 3 (base, pizza, topping); validate and re-prompt if missing/malformed. This doubles
   as a live demo of the defensive parsing.
2. **Customer** — name + phone, validated; create the order/session row, log timestamp, status=started.
3. **Select + bill** — base/pizza/topping by number, quantity; call summary → itemised bill in a
   `gr.Dataframe`/`gr.HTML`.
4. **Payment** — Cash/Card/UPI, mock confirmation, order number, append to `orders_log.txt` + DB,
   status=ordered; offer "next order".

## Process model & API wiring (DECIDED — do not re-litigate)
**One process. One port.** FastAPI hosts the REST endpoints and the Gradio UI is mounted onto it
via `gr.mount_gradio_app(api, demo, path="/")`, served by a single `uvicorn`. UI at `/`, API at
`/summary` etc., live docs at `/docs`. No second server, no separate port, no "is the server up?"
failure mode for the grader.

- **Gradio handlers call `core/` directly (in-process Python calls), NOT over HTTP.** This is the
  graded path and must stay bulletproof.
- **FastAPI endpoints are exposed alongside and call the same `core/` functions.** They exist for
  `/docs`, external callers, and Stage 3 — the UI does not depend on them.
- **Do NOT make Gradio call its own endpoints via `requests`/HTTP.** Both surfaces share `core/`;
  that is the single source of truth. (Considered and rejected: the localhost round-trip adds a
  failure mode for zero MVP benefit.)

```
app.py:  api = FastAPI();  demo = gr.Blocks(...);  app = gr.mount_gradio_app(api, demo, path="/")
         Gradio handlers ─► core/        FastAPI routes ─► core/        # same brain, no HTTP between them
```

## Deployment
- Target: **Hugging Face Spaces** for the demo — runs the single mounted process above.
- Keep secrets out of git. No live payment gateway (selection + confirmation only, per PRD).

## Conventions
- **Tooling is `uv`** (repo has uv 0.11, Python 3.14). Manage deps in `pyproject.toml` via
  `uv add ...`; run things with `uv run ...` (e.g. `uv run python app.py`, `uv run pytest`,
  `uv run uvicorn app:app`). `uv.lock` is committed. Generate a `requirements.txt` only for the
  Hugging Face Space (`uv export --no-hashes -o requirements.txt`), since HF installs from it.
- Currency is INR everywhere; round money to 2 dp at display and in the log.
- Don't hardcode menu items or prices — everything comes from the `.txt` files at runtime.
- `node_modules/` belongs to the `ppt/` slide generator; ignore it for MVP work.
- Stage 2 submission artifacts: the Gradio `.py`, the 3 `.txt` files, and a sample `orders_log.txt`.

## Don't
- Don't put gradio/fastapi/sqlalchemy imports in `core/`.
- Don't let SQLite/FastAPI become a hard dependency of the graded flow.
- Don't compute prices anywhere except `core/pricing.py`.
- Don't change the validation rules, pricing order, or log field order without checking the PRD/brief.
- Don't let any input crash the app — every prompt validates and re-prompts.
