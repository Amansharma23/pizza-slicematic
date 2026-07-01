-- SliceMatic — Stage 3: per-user orders + DB-generated order numbers
-- Run in the Supabase SQL editor (after 0001/0002). Idempotent.
--
-- Context: API/frontend-placed orders now write to Supabase ONLY (not the
-- graded orders_log.txt — the Gradio app still owns that). So the DB becomes
-- the source of truth for the app's order listing, and must:
--   1. carry a user_id (for the future auth feature; list orders by user),
--   2. generate its own human order_no (no more scanning the .txt log),
--   3. allow one row per multi-item cart (line breakdown lives in items jsonb),
--      so the per-line flat columns become optional.

-- 1. Per-user key (nullable until real auth stamps it; hardcoded demo user for now)
alter table public.orders
    add column if not exists user_id uuid;

create index if not exists idx_orders_user_id
    on public.orders (user_id, created_at desc);

-- 2. DB-generated order number, date-based: e.g. SM-20260702-0001.
--    Global sequence (no per-day reset) keeps it unique and simple. Applies only
--    when order_no is omitted on insert (API path); the Gradio mirror still
--    passes its own SM-###### from the .txt counter, which is unaffected.
create sequence if not exists public.orders_no_seq;

alter table public.orders
    alter column order_no
    set default 'SM-' || to_char(now(), 'YYYYMMDD') || '-'
        || lpad(nextval('public.orders_no_seq')::text, 4, '0');

-- 3. A cart checkout is ONE order with many items (in items jsonb). The flat
--    per-line columns don't apply to multi-item orders, so relax NOT NULL.
--    (The single-line Gradio mirror still fills them; that stays valid.)
alter table public.orders alter column base_name    drop not null;
alter table public.orders alter column pizza_name   drop not null;
alter table public.orders alter column topping_name drop not null;
alter table public.orders alter column unit_price   drop not null;
alter table public.orders alter column quantity     drop not null;
