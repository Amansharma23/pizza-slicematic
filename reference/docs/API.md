# SliceMatic AI â€” API Reference

FastAPI app: `ai/main.py`. Run locally:

```bash
uv run uvicorn ai.main:app --reload --port 7861
# interactive docs at http://localhost:7861/docs
```

Base URL (local): `http://localhost:7861`. A Postman collection is in
`postman/SliceMatic.postman_collection.json`.

Two surfaces share the same `core/` brain (menu, validation, pricing, persistence):
- **`/api/*`** â€” deterministic REST (used by the Stage 3 frontend and AI tools).
- **`/chat`, `/voice/*`** â€” conversational AI (LLM orchestrates `core/` via tools).

Every completed order is written to `orders_log.txt` (primary) **and** the Supabase
`orders` table (best-effort mirror). Money is always computed by `core/pricing.py`.

---

## Health

### GET /health
```json
{ "status": "ok", "service": "slicematic-ai" }
```

---

## Core REST (`/api`)

### GET /api/menu
Live menu from the `.txt` files.
```json
{
  "bases":    [{ "id": "B1", "name": "Thin Crust", "price": 149.0 }],
  "pizzas":   [{ "id": "P1", "name": "Margherita", "price": 299.0 }],
  "toppings": [{ "id": "T1", "name": "Black Olives", "price": 49.0 }]
}
```

### POST /api/validate/customer
Body: `{ "name": "Aman Sharma", "phone": "9811122233" }`
```json
{ "ok": true, "errors": {}, "name": "Aman Sharma", "phone": "9811122233" }
```
On failure, `ok=false` and `errors` maps field â†’ message.

### POST /api/summary
Body: `{ "base_id": "B1", "pizza_id": "P1", "topping_id": "T1", "quantity": 5 }`
```json
{ "ok": true, "bill": { "unit_price": 497.0, "subtotal": 2485.0,
  "discount": 248.5, "taxable": 2236.5, "gst": 402.57, "total": 2639.07, "quantity": 5 } }
```
Validation/menu errors â†’ `{ "ok": false, "errors": { ... } }`.

### POST /api/order
Body: `{ "name", "phone", "base_id", "pizza_id", "topping_id", "quantity", "payment_mode" }`
(`payment_mode`: `Cash`/`Card`/`UPI` or `1`/`2`/`3`). Re-validates server-side, writes log + DB.
```json
{ "ok": true, "order_no": "SM-20260630-1234", "timestamp": "2026-06-30 12:00:00",
  "payment_mode": "UPI", "name": "Aman Sharma", "bill": { ... } }
```

### GET /api/config  Â·  POST /api/config
Get/set the discount rate. POST body: `{ "discount_rate": 0.10 }` â†’ `{ "ok": true, "discount_rate": 0.10 }`.

### GET /api/analytics?filter_type=All Time
Aggregates from `orders_log.txt` (`total_orders`, `revenue`, `gst`, top items/combos, `orders_df`).

---

## Chat

### POST /chat
Body:
```json
{ "message": "I'd like 2 thin crust margherita with black olives ...", "session_id": "optional" }
```
- `session_id` optional â€” omit to start a new conversation (one is generated and returned).
- Flow: input guardrail â†’ LLM agent (tools â†’ `core/`) â†’ reply. Transcript saved to `messages`.

Response:
```json
{ "reply": "Alright, Aman! That's INR 1172.92. Confirm?", "session_id": "abc123",
  "escalated": false, "blocked": false }
```
- `blocked: true` â†’ message was redirected by the input guardrail (no LLM call); `reply` is the redirect.
- `escalated: true` â†’ the agent handed off to a human (an `escalations` row was created).

Send the returned `session_id` with each subsequent turn to continue the conversation.

---

## Voice

No telephony â€” the browser captures mic audio and plays the response.

### POST /voice/transcribe  (multipart/form-data)
Fields: `session_id` (text), `audio` (file, e.g. `audio/webm`). Enforces a 3-minute call cap.
```json
{ "session_id": "abc123", "transcript": "I want two margherita pizzas",
  "confidence": 0.99, "call_ended": false }
```
`call_ended: true` when the 3-minute cap is exceeded (stop the call). On STT failure:
`{ "transcript": "", "error": "transcription_failed" }`.

### POST /voice/respond
Body: `{ "transcript": "...", "session_id": "optional" }`. Same agent as `/chat`, `channel=voice`.
Response shape matches `/chat` (`reply`, `session_id`, `escalated`, `blocked`).

### POST /voice/synthesize
Body: `{ "text": "Your order is confirmed!", "language": "en" }`.
Returns **`audio/mpeg`** bytes (Deepgram Aura). Hindi TTS is a Phase-2 swap (Google/Azure).

---

## Notes
- **CORS**: set `AI_CORS_ORIGINS` (comma-separated) for the Next.js origin; default `*`.
- **Auth**: none yet (demo). Add an API key / origin allowlist before any public deploy.
- **Resilience**: Supabase writes are best-effort with transient-error retries; a DB outage
  does not replace the Stage 3 database-backed order path.
- **Models**: primary `google/gemini-2.5-flash`, fallbacks `anthropic/claude-haiku-4.5`,
  `openai/gpt-4o-mini` (via OpenRouter); input-guardrail classifier `openai/gpt-4o-mini`.
