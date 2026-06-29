# Stage 2 Run Guide

SliceMatic Stage 2 is a Gradio MVP for the PizzaFlow assignment. It loads menu files at runtime, validates customer/order input, calculates discount and GST, accepts a mock payment mode, and writes completed orders to a parseable log.

## Requirements

- Python 3.12 or newer.
- Recommended: `uv`.

## Run With uv

```powershell
uv run python app.py
```

Open:

```text
http://127.0.0.1:7860/
```

## Run Without uv On Windows

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open:

```text
http://127.0.0.1:7860/
```

## Stage 2 Files

- Gradio app: `app.py`
- Menu files: `menu_data/Types_of_Base.txt`, `menu_data/Types_of_Pizza.txt`, `menu_data/Types_of_Toppings.txt`
- Order log: `database/orders_log.txt`
- Core logic: `core/menu.py`, `core/validation.py`, `core/pricing.py`, `core/persistence.py`

Completed orders are stored as:

```text
order_id | timestamp | name | phone | base | pizza | topping | unit_price | quantity | subtotal | discount | gst | total | payment_mode
```

## Admin Menu Behavior

- `Use SliceMatic default menu` loads from `menu_data/`.
- `Upload my own menu files` stores the active custom menu in `database/menu/`.
- Admin can update one, two, or all three menu files.
- After an update, the admin page shows Previous menu vs New menu.
- Added or changed items are highlighted green in the New menu.
- Removed items are highlighted red in the Previous menu.

## Smoke Test

Run this before submission:

```powershell
.\.venv\Scripts\python.exe scripts\stage2_smoke_test.py
```

Or with `uv`:

```powershell
uv run python scripts/stage2_smoke_test.py
```

The smoke test:

- starts the app on port `7870`,
- loads temporary swapped menu files,
- places one order through the API,
- verifies pricing, discount, GST, and total,
- verifies an order log was written to `database/smoke_test_data/smoke_orders_log.txt`,
- stops the test app.

By default, the smoke-test log is kept so it can be shown to a judge. To delete it automatically after verification, open `scripts/stage2_smoke_test.py` and set:

```python
DELETE_SMOKE_DATA_AFTER_TEST = True
```

Expected final output:

```text
PASS
```

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Or:

```powershell
uv run pytest
```
