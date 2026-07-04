# SliceMatic Admin - Stage 0 Local Setup

This is the local setup path for Aman's Admin-module work. Secrets live in
`.env` and `frontend/.env.local`; both are gitignored.

## What Is Configured

- Backend/API: FastAPI on `http://127.0.0.1:7861`
- Gradio app: `http://127.0.0.1:7860`
- Frontend: Next.js on `http://localhost:3000`
- Local DB: PostgreSQL 16, database `slicematic_local`
- DB provider switch: `DATABASE_PROVIDER=postgres`
- Admin dev user: `admin@slicematic.local`
- Admin dev token: configured in `.env` as `ADMIN_DEV_TOKEN`
- Staff dev user: `kitchen@slicematic.local`
- Staff dev token: configured in `.env` as `STAFF_DEV_TOKEN`
- Future Supabase switch: set `DATABASE_PROVIDER=supabase` and fill Supabase envs

## Installed Locally

- PostgreSQL 16 via winget
- uv via winget
- Python packages in `.venv`
- Frontend packages under `frontend/node_modules`

Postgres binary path on this machine:

```powershell
C:\Program Files\PostgreSQL\16\bin
```

If `uv` is not visible in the current terminal, restart PowerShell so PATH picks
up the winget installation.

## Local Database

The local database was created with:

- database: `slicematic_local`
- user: `slicematic_user`
- password: local-only password stored in `.env`

Existing migrations applied:

```text
supabase/migrations/0001_init_ai_schema.sql
supabase/migrations/0002_escalations.sql
supabase/migrations/0003_orders_user_and_number.sql
supabase/migrations/0004_admin_foundation.sql
supabase/migrations/0005_admin_core_management.sql
supabase/migrations/0006_admin_operations.sql
supabase/migrations/0007_admin_analytics_ai.sql
supabase/migrations/0008_notifications_settings.sql
supabase/migrations/0009_staff_discounts_crud.sql
supabase/migrations/0010_operational_workflows.sql
supabase/migrations/0011_staff_kitchen_surface.sql
supabase/migrations/0012_staff_pos_source.sql
supabase/migrations/0013_inventory_recipes_deductions.sql
```

Manual migration command:

```powershell
$env:PGPASSWORD='postgres'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0001_init_ai_schema.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0002_escalations.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0003_orders_user_and_number.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0004_admin_foundation.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0005_admin_core_management.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0006_admin_operations.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0007_admin_analytics_ai.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0008_notifications_settings.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0009_staff_discounts_crud.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0010_operational_workflows.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0011_staff_kitchen_surface.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0012_staff_pos_source.sql'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -U postgres -d slicematic_local -f 'supabase\migrations\0013_inventory_recipes_deductions.sql'
```

## Run Commands

Backend API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ai.main:app --host 127.0.0.1 --port 7861
```

Gradio:

```powershell
.\.venv\Scripts\python.exe app.py
```

Frontend:

```powershell
cd frontend
npm run dev
```

Repeatable demo data for judging:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

## Current Verification

- `GET http://127.0.0.1:7861/health` returns ok.
- `GET http://127.0.0.1:7861/api/menu` returns menu data.
- `GET http://localhost:3000/admin` returns 200.
- Protected `GET http://127.0.0.1:7861/admin/me` returns the seeded admin user
  when called with `Authorization: Bearer <ADMIN_DEV_TOKEN>`.
- Admin pages are available at `/admin`, `/admin/menu`, `/admin/pricing`,
  `/admin/orders`, `/admin/inventory`, `/admin/payments`, `/admin/analytics`,
  `/admin/ai-insights`, `/admin/notifications`, `/admin/settings`,
  `/admin/staff`, and `/admin/audit-logs`.
- Operational admin workflows now include menu create/soft-delete, refund
  decisions, and inventory request decisions.
- Staff kitchen queue is available at `/staff`; protected staff APIs are
  available at `/staff/me`, `/staff/orders`, and `/staff/inventory`.
- Staff POS checkout is available in `/staff` and through protected
  `/staff/checkout`; orders enter the kitchen queue as `Confirmed`.
- Inventory recipe mappings are managed from `/admin/inventory`; moving mapped
  orders to `Preparing` automatically deducts ingredient stock once.
- Local Postgres order create/list works through `db.orders`.
- Demo seed script populates orders, payments, refunds, notifications,
  inventory movements, price history, and AI recommendation events.
- `npm run lint` passes.
- Focused backend tests pass:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_pricing.py tests\test_validation.py tests\test_cart_api.py
```

## Notes

- Admin AI provider abstraction is implemented. Local mode uses
  `ADMIN_AI_PROVIDER=mock`; switch to `openai`, `gemini`, or `openrouter`
  after adding the matching API key and optional `ADMIN_AI_MODEL`.
- Existing customer chat still requires `OPENROUTER_API_KEY`; without it the
  API service starts, but chat AI calls will fail.
- npm reported two moderate audit findings and one Node engine warning because
  this machine uses Node 23.11.0. Node 22 LTS or Node 24+ is preferred.
