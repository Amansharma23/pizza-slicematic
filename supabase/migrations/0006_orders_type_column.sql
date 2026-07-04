-- SliceMatic — orders.type column (order classification, e.g. online vs
-- in-store/future channels). Run in the Supabase SQL editor (after 0005).
-- Idempotent.
--
-- Context: added ad-hoc via `ALTER TABLE public.orders ADD COLUMN type text;`
-- — captured here so the schema stays reproducible like 0001-0005. db/orders.py
-- (create_order, list_orders_by_user, list_recent_orders, list_orders_by_phone)
-- and api/routes.py (POST /api/cart/checkout, GET /api/orders[/recent]) already
-- read/write/filter this column; existing rows are NULL until backfilled.

alter table public.orders
    add column if not exists type text;

create index if not exists idx_orders_type_status
    on public.orders (type, status, created_at desc);


alter table public.orders drop constraint if exists orders_status_check;
alter table public.orders add constraint orders_status_check
    check (status in (
        'received', 'preparing', 'ready_for_pickup', 'out_for_delivery',
        'delivered', 'confirmed', 'cancelled'
    ));