# SliceMatic Admin - Supabase Setup

The admin, staff, customer auth, orders, inventory, analytics, and settings
surfaces now run in Supabase mode without a local Postgres server.

## Required `.env`

```env
DATABASE_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

ADMIN_DEV_EMAIL=admin@slicematic.local
ADMIN_DEV_TOKEN=replace-with-local-dev-token
STAFF_DEV_EMAIL=kitchen@slicematic.local
STAFF_DEV_TOKEN=replace-with-local-staff-token
```

`DATABASE_URL` is not required for Supabase-only mode.

## Database Schema

Apply the files in `supabase/migrations/` to your Supabase project, in filename
order. You can use the Supabase SQL editor, Supabase CLI, or any SQL runner
connected to the Supabase project.

After migrations, seed demo accounts:

```powershell
uv run python scripts/seed_demo_users.py
```

## Run

Backend API:

```powershell
uv run uvicorn ai.main:app --host 127.0.0.1 --port 7861
```

Frontend:

```powershell
cd frontend
npm run dev
```

Open:

- Customer app: `http://localhost:3000`
- Admin: `http://localhost:3000/admin`
- Staff: `http://localhost:3000/staff`
- API health: `http://127.0.0.1:7861/health`

## Verified Supabase Routes

With `DATABASE_PROVIDER=supabase`, these protected routes read/write through
the Supabase service API:

- `/admin/me`
- `/admin/dashboard`
- `/admin/menu`
- `/admin/pricing`
- `/admin/staff`
- `/admin/orders`
- `/admin/inventory`
- `/admin/analytics`
- `/admin/notifications`
- `/admin/settings`
- `/staff/me`
- `/staff/orders`
- `/staff/inventory`

The old direct SQL admin backend is still present as a fallback for
`DATABASE_PROVIDER=postgres`, but it is no longer required for local Supabase
development.
