# SliceMatic — Backend API Schema Reference

Generated from the live OpenAPI schema (`GET /openapi.json`) + route handlers.
**Base URL (local):** `http://localhost:7861` · Interactive docs: `http://localhost:7861/docs`

All bodies are JSON unless noted (voice uses form-data). Money is INR, computed only by
`core/pricing.py`. Every endpoint under `/api/*`, `/chat`, `/voice/*` lives in the one FastAPI
service (`ai.main:app`).

---

## Conventions

- **Business errors** return HTTP `200` with `{"ok": false, "errors": {<field>: <message>}}`.
  Only **auth/token** failures use HTTP `401`/`403`. Bad JSON shape → HTTP `422`.
- **Auth:** JWT bearer. Send `Authorization: Bearer <token>` on protected routes.
  Get a token from `/api/auth/login` or `/api/auth/signup`.
- Success responses generally carry `{"ok": true, ...}`.

### Shared value rules (enforced server-side by `core/validation.py`)

| Field | Rule |
|---|---|
| `name` | Alphabets + spaces only, 2–40 chars, not blank |
| `phone` | Exactly 10 digits, first digit ∈ {6,7,8,9} |
| `quantity` | Integer 1–10 (accepts string or int; `"three"`, `0`, `11` rejected) |
| `pin` | Exactly 6 digits |
| `payment_mode` | `"1"`=Cash, `"2"`=Card, `"3"`=UPI (send the digit as a string) |
| `role` | `user` · `admin` · `staff` · `kitchen_staff` · `delivery` |
| menu ids (`base_id`/`pizza_id`/`topping_id`) | must exist in the live menu (`GET /api/menu`) |

> Frontend mapping: COD & Cash → `"1"` (Cash); UPI → `"3"`. Card (`"2"`) is unused by the UI.

---

## 🔐 Auth & Accounts — `/api/auth/*`

### `POST /api/auth/signup` — customers only
Request (`SignupReq`):
```json
{ "name": "Asha Rao", "phone": "9876543210", "pin": "123456", "confirm_pin": "123456" }
```
Success: `{ "ok": true, "token": "<jwt>", "user": { ...account... } }`
Errors: per-field under `errors` (`name`, `phone`, `pin`), or `phone` already registered.

### `POST /api/auth/login` — all roles
Request (`LoginReq`) — note the **generic** field names:
```json
{ "role": "user", "identifier": "9876543210", "secret": "123456" }
```
| role | `identifier` is | `secret` is |
|---|---|---|
| `user` | phone (10 digits) | 6-digit PIN |
| `admin` | email (lowercased) | password |
| `staff` / `kitchen_staff` / `delivery` | `emp_id` (e.g. `SMEMP001`) | 6-digit PIN |

Success: `{ "ok": true, "token": "<jwt>", "user": {...} }`
Failure: `{ "ok": false, "errors": { "credentials": "..." } }` (one generic message — never
reveals which part was wrong). **5 wrong attempts → 15-min lockout.**

### `GET /api/auth/me` 🔒
Returns `{ "ok": true, "user": {...} }` for the bearer token's account.

### `PUT /api/auth/me/address` 🔒 (customer)
Request (`AddressReq`) — a list of address objects:
```json
{ "address": [
  { "id": "addr-1", "label": "Home", "line": "12 New Ashok Nagar, Delhi", "isDefault": true }
] }
```
`line` is required per entry; `label` defaults to `"Home"`. Returns the updated `user`.

### `GET /api/auth/employees` 🔒 admin
`{ "ok": true, "employees": [...] }`

### `POST /api/auth/employees` 🔒 admin — create staff/kitchen/delivery
Request (`EmployeeCreateReq`):
```json
{ "name": "Ravi K", "phone": "9811122233", "role": "staff", "pin": "654321" }
```
`role` ∈ {`staff`,`kitchen_staff`,`delivery`}. Returns `{ "ok": true, "employee": { ...emp_id... } }`.
Admin shares the `emp_id` + PIN with the employee out-of-band.

### `PATCH /api/auth/employees/{user_id}` 🔒 admin — reset PIN / (de)activate
Request (`EmployeeUpdateReq`), send either or both:
```json
{ "is_active": false, "pin": "111111" }
```
Setting `pin` also clears any lockout. Returns `{ "ok": true, "employee": {...} }`.

---

## 🍕 Menu & Pricing — `/api/*`

### `GET /api/menu`
No params. Returns the live menu (grader-swappable `.txt` → resolved):
```json
{ "bases":   [ { "id": "1", "name": "Thin Crust", "price": 0 }, ... ],
  "pizzas":  [ { "id": "1", "name": "Margherita",  "price": 199 }, ... ],
  "toppings":[ { "id": "1", "name": "Extra Cheese", "price": 69 }, ... ] }
```
On a bad menu file: `{ "error": "<MenuError message>" }`.

### `POST /api/validate/customer`
Request (`CustomerReq`): `{ "name": "...", "phone": "..." }`
Returns `{ "ok": bool, "errors": {...}, "name": <clean|null>, "phone": <clean|null> }`.

### `POST /api/summary` — price ONE line (single topping)
Request (`SummaryReq`):
```json
{ "base_id": "1", "pizza_id": "2", "topping_id": "3", "quantity": 5 }
```
Success: `{ "ok": true, "bill": { unit_price, quantity, subtotal, discount, gst, total, ... } }`.
`quantity` may be a string or int; invalid ids/qty → `{ "ok": false, "errors": {...} }`.

### `POST /api/cart/price` — price a MULTI-line, MULTI-topping cart
Request (`CartReq`): each line has **1–3** `topping_ids`.
```json
{ "lines": [
  { "base_id": "1", "pizza_id": "2", "topping_ids": ["3","4"], "quantity": "2" }
] }
```
Success:
```json
{ "ok": true,
  "lines": [ { ...per-line bill... } ],
  "cart":  { "subtotal": 0, "discount": 0, "taxable": 0, "gst": 0, "total": 0 } }
```
First bad line → `{ "ok": false, "line_index": <i>, "errors": {...} }`. Money summed from
per-line `core.compute_bill` — never client-side.

---

## 🧾 Orders — `/api/*`

### `POST /api/order` — single-line order (vanilla `web/`; writes `orders_log.txt` + DB mirror)
Request (`OrderReq`):
```json
{ "base_id": "1", "pizza_id": "2", "topping_id": "3", "quantity": 5,
  "name": "Asha Rao", "phone": "9876543210", "payment_mode": "1" }
```
Success: `{ "ok": true, "order_no": "SM-000001", "timestamp": "...", "payment_mode": "Cash",
"name": "...", "bill": {...} }`.

### `POST /api/cart/checkout` — multi-line cart (DB-ONLY, source of truth)
Request (`CheckoutReq`):
```json
{ "user_id": "<uuid|>", "name": "Asha Rao", "phone": "9876543210",
  "payment_mode": "1", "address": "12 New Ashok Nagar, Delhi",
  "type": "online",
  "lines": [ { "base_id": "1", "pizza_id": "2", "topping_ids": ["3"], "quantity": "1" } ] }
```
- `payment_mode`: `"1"` Cash/COD · `"3"` UPI. `type` defaults `"online"`.
- Success: `{ "ok": true, "order_no": "SM-YYYYMMDD-NNNN", "total": <num>, "name": "...",
  "payment_mode": "Cash", "line_count": <n> }`.
- **No `.txt` fallback** — a DB failure is surfaced: `{ "ok": false, "errors": { "db": "..." } }`.
  `order_no` is generated by the DB.

### `GET /api/orders` — a user's orders (newest first)
Query params (all optional): `user_id`, `phone`, `type`, `status`. **`phone` wins if both sent.**
> Interim: filter is enumerable; the authorization step will derive the user from the JWT.

### `GET /api/orders/recent` — ALL recent orders (delivery queue)
Query params (optional): `type`, `status`. Every rider sees every order (interim).

### `GET /api/config` / `POST /api/config` — runtime discount config
`POST` request (`ConfigReq`): `{ "discount_rate": 0.10, "discount_threshold": 5 }`
(`discount_rate` required; threshold defaults 5).

### `GET /api/analytics`
Query params (optional): `filter_type` (default `"All Time"`), `start_date`, `end_date`.

### `GET /api/health` / `GET /health`
`{ "status": "ok", ... }` — no auth.

---

## 💬 Chat — `/chat`

### `POST /chat`
Optional header `Authorization: Bearer <token>`.
Request (`ChatRequest`):
```json
{ "message": "I want 2 margherita pizzas", "session_id": "<optional; created if absent>" }
```
Response (`ChatResponse`):
```json
{ "reply": "…", "session_id": "…", "escalated": false, "blocked": false }
```
`blocked` = input guardrail tripped; `escalated` = handed to a human. Needs
`OPENROUTER_API_KEY` set. Bill/payment UI is injected via `[BILL]…[/BILL]` /
`[PAYMENT_OPTIONS]` tags inside `reply`.

---

## 🎙️ Voice — `/voice/*` (browser mic; no telephony)

3-minute per-call cap. **Currently disabled in the frontend** (`VOICE_ENABLED = false`), but the
endpoints are live.

### `POST /voice/start` — form-urlencoded
`session_id=<id>` → resets the 3-min budget. Returns `{...}`.

### `POST /voice/transcribe` — multipart/form-data
Fields: `session_id` (string), `audio` (binary blob, `audio/webm;codecs=opus`).
Returns `{ "transcript": "...", "call_ended": <bool>, ... }` (Deepgram Nova-2, `language=multi`).

### `POST /voice/respond`
Optional `Authorization` header. Request (`VoiceRespondRequest`):
```json
{ "transcript": "…", "session_id": "<optional>" }
```
Runs the input guardrail → agent loop → returns the text reply + state.

### `POST /voice/synthesize`
Request (`SynthesizeRequest`): `{ "text": "…", "language": "en" }`
Returns audio (Deepgram Aura for English; Hindi TTS via Sarvam is the marked swap).

### `WS /voice/call`
Realtime streaming voice call (Sarvam streaming). Frontend derives the URL by swapping
`http`→`ws` on the API base.

---

## Quick reference — request models

| Model | Fields |
|---|---|
| `SignupReq` | `name`, `phone`, `pin`, `confirm_pin` |
| `LoginReq` | `role`(=`user`), `identifier`, `secret` |
| `AddressReq` | `address: [ {id,label,line,isDefault} ]` |
| `EmployeeCreateReq` | `name`, `phone`, `role`, `pin` |
| `EmployeeUpdateReq` | `is_active?`, `pin?` |
| `CustomerReq` | `name`, `phone` |
| `SummaryReq` | `base_id`, `pizza_id`, `topping_id`, `quantity` |
| `OrderReq` | `base_id`, `pizza_id`, `topping_id`, `quantity`, `name`, `phone`, `payment_mode` |
| `CartLineReq` | `base_id`, `pizza_id`, `topping_ids[1..3]`, `quantity` |
| `CartReq` | `lines: [CartLineReq]` |
| `CheckoutReq` | `user_id`, `name`, `phone`, `payment_mode`, `address`, `type`, `lines[]` |
| `ConfigReq` | `discount_rate`, `discount_threshold`(=5) |
| `ChatRequest` | `message`, `session_id?` |
| `VoiceRespondRequest` | `transcript`, `session_id?` |
| `SynthesizeRequest` | `text`, `language`(=`en`) |
