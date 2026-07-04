-- SliceMatic — kitchen/delivery status pipeline timestamps.
-- Run in the Supabase SQL editor (after 0006). Idempotent.
--
-- Context: status can only ever be set once today (create_order defaults it
-- to "received"). This adds one timestamp per transition in the new
-- received -> preparing -> ready_for_pickup -> out_for_delivery -> delivered
-- state machine (db/orders.py:update_order_status), so "time taken picked up
-- to delivered" is directly computable (out_for_delivery_at -> delivered_at).

alter table public.orders
    add column if not exists preparing_at timestamptz,
    add column if not exists ready_at timestamptz,
    add column if not exists out_for_delivery_at timestamptz,
    add column if not exists delivered_at timestamptz;

create index if not exists idx_orders_type_status_created
    on public.orders (type, status, created_at desc);

-- 0001_init_ai_schema.sql's original check only allowed
-- ('received','confirmed','cancelled') — too narrow for the new pipeline.
-- Widen it to the full ORDER_STATUS_SEQUENCE (db/orders.py) plus the
-- pre-existing 'confirmed'/'cancelled' values so old rows stay valid.
alter table public.orders drop constraint if exists orders_status_check;
alter table public.orders add constraint orders_status_check
    check (status in (
        'received', 'preparing', 'ready_for_pickup', 'out_for_delivery',
        'delivered', 'confirmed', 'cancelled'
    ));
