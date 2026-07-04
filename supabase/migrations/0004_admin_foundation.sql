-- SliceMatic Stage 3 - Admin foundation
-- Idempotent RBAC seed for local Postgres now and Supabase Postgres later.

create extension if not exists pgcrypto;

create table if not exists public.app_users (
    id            uuid primary key default gen_random_uuid(),
    email         text not null unique,
    full_name     text not null,
    phone         text,
    status        text not null default 'active'
                  check (status in ('active', 'inactive')),
    password_hash text,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

create table if not exists public.roles (
    id          uuid primary key default gen_random_uuid(),
    name        text not null unique,
    description text,
    created_at  timestamptz not null default now()
);

create table if not exists public.permissions (
    id          uuid primary key default gen_random_uuid(),
    code        text not null unique,
    description text,
    created_at  timestamptz not null default now()
);

create table if not exists public.user_roles (
    user_id uuid not null references public.app_users(id) on delete cascade,
    role_id uuid not null references public.roles(id) on delete cascade,
    primary key (user_id, role_id)
);

create table if not exists public.role_permissions (
    role_id       uuid not null references public.roles(id) on delete cascade,
    permission_id uuid not null references public.permissions(id) on delete cascade,
    primary key (role_id, permission_id)
);

create table if not exists public.audit_logs (
    id           uuid primary key default gen_random_uuid(),
    action_type  text not null,
    entity_type  text not null,
    entity_id    text,
    old_value    jsonb,
    new_value    jsonb,
    performed_by uuid references public.app_users(id) on delete set null,
    performed_at timestamptz not null default now(),
    reason       text
);

create index if not exists idx_audit_logs_performed_at
    on public.audit_logs (performed_at desc);

create index if not exists idx_audit_logs_entity
    on public.audit_logs (entity_type, entity_id);

insert into public.roles (name, description) values
    ('Admin', 'Full access to SliceMatic owner controls.'),
    ('Manager', 'Daily operations, orders, inventory, menu, analytics, and refunds.'),
    ('Customer Facing Staff', 'POS, customer/order details, bills, and refund requests.'),
    ('Backstage Staff', 'Kitchen orders, order status updates, and inventory requests.'),
    ('Customer', 'Customer ordering, history, and updates.')
on conflict (name) do update set description = excluded.description;

insert into public.permissions (code, description) values
    ('admin.access', 'Access the admin surface.'),
    ('admin.dashboard.read', 'Read admin dashboard metrics.'),
    ('orders.read', 'Read all orders.'),
    ('orders.update_status', 'Update order statuses.'),
    ('menu.manage', 'Manage menu items and availability.'),
    ('pricing.manage', 'Manage pricing, GST, and discounts.'),
    ('inventory.manage', 'Manage inventory and stock transactions.'),
    ('staff.manage', 'Manage staff users and roles.'),
    ('refunds.manage', 'Approve or reject refunds.'),
    ('analytics.read', 'Read analytics dashboards.'),
    ('ai.insights.read', 'Read AI insight summaries.'),
    ('audit.read', 'Read audit logs.')
on conflict (code) do update set description = excluded.description;

insert into public.app_users (id, email, full_name, phone, status)
values (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'admin@slicematic.local',
    'Aman Admin',
    '9876543210',
    'active'
)
on conflict (email) do update set
    full_name = excluded.full_name,
    phone = excluded.phone,
    status = excluded.status,
    updated_at = now();

insert into public.user_roles (user_id, role_id)
select u.id, r.id
from public.app_users u
join public.roles r on r.name = 'Admin'
where u.email = 'admin@slicematic.local'
on conflict do nothing;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
cross join public.permissions p
where r.name = 'Admin'
on conflict do nothing;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
join public.permissions p on p.code in (
    'admin.access',
    'admin.dashboard.read',
    'orders.read',
    'orders.update_status',
    'menu.manage',
    'pricing.manage',
    'inventory.manage',
    'refunds.manage',
    'analytics.read',
    'ai.insights.read',
    'audit.read'
)
where r.name = 'Manager'
on conflict do nothing;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
join public.permissions p on p.code in ('orders.read')
where r.name = 'Customer Facing Staff'
on conflict do nothing;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
join public.permissions p on p.code in ('orders.read', 'orders.update_status')
where r.name = 'Backstage Staff'
on conflict do nothing;
