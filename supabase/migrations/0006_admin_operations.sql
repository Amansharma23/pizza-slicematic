-- SliceMatic Stage 3 - Admin operations
-- Orders lifecycle, payments/refunds, and inventory foundations.

create extension if not exists pgcrypto;

alter table public.orders drop constraint if exists orders_status_check;
alter table public.orders
    add constraint orders_status_check check (status in (
        'Created',
        'PaymentPending',
        'Confirmed',
        'Preparing',
        'Ready',
        'Delivered',
        'Completed',
        'Cancelled',
        'RefundRequested',
        'Refunded',
        'received',
        'confirmed',
        'cancelled'
    ));

create table if not exists public.order_status_history (
    id          uuid primary key default gen_random_uuid(),
    order_id    uuid not null references public.orders(id) on delete cascade,
    old_status  text,
    new_status  text not null,
    changed_by  uuid references public.app_users(id) on delete set null,
    changed_at  timestamptz not null default now(),
    reason      text
);

create table if not exists public.payments (
    id          uuid primary key default gen_random_uuid(),
    order_id    uuid not null references public.orders(id) on delete cascade,
    payment_mode text not null check (payment_mode in ('Cash', 'Card', 'UPI')),
    payment_status text not null default 'Paid'
        check (payment_status in ('Pending', 'Paid', 'Failed', 'Refunded')),
    amount_paid numeric not null default 0 check (amount_paid >= 0),
    transaction_reference text,
    paid_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists public.refunds (
    id          uuid primary key default gen_random_uuid(),
    order_id    uuid not null references public.orders(id) on delete cascade,
    payment_id  uuid references public.payments(id) on delete set null,
    amount      numeric not null check (amount >= 0),
    reason      text not null,
    status      text not null default 'Requested'
        check (status in ('Requested', 'Approved', 'Rejected', 'Paid')),
    requested_by uuid references public.app_users(id) on delete set null,
    approved_by  uuid references public.app_users(id) on delete set null,
    requested_at timestamptz not null default now(),
    decided_at   timestamptz
);

create table if not exists public.ingredients (
    id          uuid primary key default gen_random_uuid(),
    name        text not null unique,
    unit        text not null default 'kg',
    stock_quantity numeric not null default 0 check (stock_quantity >= 0),
    reorder_threshold numeric not null default 0 check (reorder_threshold >= 0),
    is_active   boolean not null default true,
    updated_at  timestamptz not null default now()
);

create table if not exists public.stock_transactions (
    id            uuid primary key default gen_random_uuid(),
    ingredient_id uuid not null references public.ingredients(id) on delete cascade,
    transaction_type text not null check (transaction_type in ('StockIn', 'StockOut', 'Wastage')),
    quantity      numeric not null check (quantity > 0),
    old_quantity  numeric not null,
    new_quantity  numeric not null check (new_quantity >= 0),
    reason        text,
    performed_by  uuid references public.app_users(id) on delete set null,
    performed_at  timestamptz not null default now()
);

create table if not exists public.inventory_requests (
    id            uuid primary key default gen_random_uuid(),
    ingredient_id uuid references public.ingredients(id) on delete set null,
    requested_quantity numeric not null check (requested_quantity > 0),
    status        text not null default 'Requested'
        check (status in ('Requested', 'Approved', 'Rejected')),
    requested_by  uuid references public.app_users(id) on delete set null,
    decided_by    uuid references public.app_users(id) on delete set null,
    reason        text,
    created_at    timestamptz not null default now(),
    decided_at    timestamptz
);

create index if not exists idx_order_status_history_order
    on public.order_status_history (order_id, changed_at desc);
create index if not exists idx_payments_order on public.payments (order_id);
create index if not exists idx_refunds_status on public.refunds (status, requested_at desc);
create index if not exists idx_ingredients_low_stock
    on public.ingredients (is_active, stock_quantity, reorder_threshold);

insert into public.ingredients (name, unit, stock_quantity, reorder_threshold) values
    ('Mozzarella Cheese', 'kg', 8, 5),
    ('Pizza Sauce', 'litre', 6, 4),
    ('Thin Crust Base', 'piece', 18, 20),
    ('Paneer Cubes', 'kg', 4, 3),
    ('Chicken Tikka', 'kg', 3, 4),
    ('Sweet Corn', 'kg', 5, 2)
on conflict (name) do update set
    unit = excluded.unit,
    stock_quantity = excluded.stock_quantity,
    reorder_threshold = excluded.reorder_threshold,
    updated_at = now();

insert into public.payments (order_id, payment_mode, payment_status, amount_paid, paid_at)
select o.id,
       case
           when o.payment_mode in ('Cash', 'Card', 'UPI') then o.payment_mode
           else 'Cash'
       end,
       case
           when o.status in ('PaymentPending') then 'Pending'
           else 'Paid'
       end,
       o.total,
       o.created_at
from public.orders o
where not exists (
    select 1 from public.payments p where p.order_id = o.id
);

insert into public.order_status_history (order_id, old_status, new_status, reason)
select o.id, null, o.status, 'Seeded from existing order status'
from public.orders o
where not exists (
    select 1 from public.order_status_history h where h.order_id = o.id
);
