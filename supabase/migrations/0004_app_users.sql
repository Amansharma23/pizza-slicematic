-- SliceMatic — Stage 3: user management + role management (authentication)
-- Run in the Supabase SQL editor (after 0001/0002/0003). Idempotent.
--
-- One table for every account, distinguished by `role`:
--   * user          — customer app (/). Signs in with phone + 6-digit PIN.
--   * admin         — dashboard (/admin). Signs in with email + password.
--                     Seeded via scripts/seed_admin.py — no public admin signup.
--   * staff         — kiosk (/staff). emp_id + PIN, created from the admin panel.
--   * kitchen_staff — kiosk (/kitchen). emp_id + PIN, created from the admin panel.
--   * delivery      — mobile (/delivery). emp_id + PIN, created from the admin panel.
--
-- Secrets (PIN or password) are stored ONLY as bcrypt hashes (secret_hash).
-- failed_attempts / locked_until implement brute-force lockout — mandatory
-- because a 6-digit PIN is only 1M combinations.

create extension if not exists pgcrypto;

create table if not exists public.app_users (
    id              uuid primary key default gen_random_uuid(),
    role            text not null check (role in
                        ('user', 'admin', 'staff', 'kitchen_staff', 'delivery')),
    name            text not null,
    phone           text unique,           -- customers + employees (unique login key for customers)
    email           text unique,           -- admin login key
    emp_id          text unique,           -- employee login key, DB-generated (SMEMP001, ...)
    secret_hash     text not null,         -- bcrypt hash of the PIN or password
    address         jsonb,                 -- customer delivery addresses: [{id,label,line,isDefault}]
    is_active       boolean not null default true,
    failed_attempts int not null default 0,
    locked_until    timestamptz,
    created_at      timestamptz not null default now()
);

create index if not exists idx_app_users_role on public.app_users (role);

-- Auto-generate emp_id for employee roles when it isn't supplied.
create sequence if not exists public.emp_id_seq;

create or replace function public.assign_emp_id()
returns trigger
language plpgsql
as $$
begin
    if new.role in ('staff', 'kitchen_staff', 'delivery') and new.emp_id is null then
        -- Brand format SMEMP001 (0005 re-applies this on DBs that ran the
        -- original 0004, which used EMP-001).
        new.emp_id := 'SMEMP' || lpad(nextval('public.emp_id_seq')::text, 3, '0');
    end if;
    return new;
end;
$$;

drop trigger if exists trg_assign_emp_id on public.app_users;
create trigger trg_assign_emp_id
    before insert on public.app_users
    for each row execute function public.assign_emp_id();

-- Orders now carry the delivery address chosen at checkout, so the delivery
-- rider's screen can show where each order goes.
alter table public.orders
    add column if not exists delivery_address text;
