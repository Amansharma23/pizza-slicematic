-- SliceMatic Stage 3 - Notifications and settings foundation

create extension if not exists pgcrypto;

create table if not exists public.notification_logs (
    id uuid primary key default gen_random_uuid(),
    channel text not null check (channel in ('whatsapp', 'email', 'mock')),
    provider text not null default 'mock',
    recipient text not null,
    template_name text not null,
    payload jsonb not null default '{}'::jsonb,
    status text not null default 'queued'
        check (status in ('queued', 'sent', 'failed', 'mocked')),
    error_message text,
    related_entity_type text,
    related_entity_id text,
    created_by uuid references public.app_users(id) on delete set null,
    created_at timestamptz not null default now(),
    sent_at timestamptz
);

create table if not exists public.whatsapp_messages (
    id uuid primary key default gen_random_uuid(),
    notification_id uuid references public.notification_logs(id) on delete cascade,
    phone text not null,
    message text not null,
    provider_message_id text,
    status text not null default 'mocked',
    created_at timestamptz not null default now()
);

create table if not exists public.email_logs (
    id uuid primary key default gen_random_uuid(),
    notification_id uuid references public.notification_logs(id) on delete cascade,
    email text not null,
    subject text not null,
    body text not null,
    provider_message_id text,
    status text not null default 'mocked',
    created_at timestamptz not null default now()
);

create index if not exists idx_notification_logs_created_at
    on public.notification_logs (created_at desc);
create index if not exists idx_notification_logs_channel
    on public.notification_logs (channel, status, created_at desc);

insert into public.app_settings (key, value) values
    ('restaurant_name', '{"value": "SliceMatic"}'),
    ('restaurant_gstin', '{"value": ""}'),
    ('restaurant_phone', '{"value": "9876543210"}'),
    ('restaurant_address', '{"value": "New Ashok Nagar, Delhi"}'),
    ('notification_whatsapp_provider', '{"value": "mock"}'),
    ('notification_email_provider', '{"value": "mock"}')
on conflict (key) do nothing;
