-- SliceMatic Stage 6B - Staff POS source
-- Allow staff-created counter orders to be tracked separately from customer API orders.

alter table public.orders drop constraint if exists orders_source_check;
alter table public.orders
    add constraint orders_source_check check (
        source in ('app', 'api', 'ai', 'voice', 'staff_pos')
    );
