-- SliceMatic Stage 3 - Analytics and AI insight logs
-- Summary tables are ready for scheduled aggregation later; current APIs compute
-- from source tables so dashboard data stays live.

create extension if not exists pgcrypto;

create table if not exists public.daily_sales_summary (
    summary_date date primary key,
    total_orders int not null default 0,
    revenue numeric not null default 0,
    gst numeric not null default 0,
    discount numeric not null default 0,
    average_order_value numeric not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.hourly_sales_summary (
    summary_date date not null,
    hour int not null check (hour >= 0 and hour <= 23),
    total_orders int not null default 0,
    revenue numeric not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (summary_date, hour)
);

create table if not exists public.menu_item_sales_summary (
    item_name text not null,
    item_type text not null default 'pizza',
    quantity int not null default 0,
    revenue numeric not null default 0,
    summary_from date not null,
    summary_to date not null,
    updated_at timestamptz not null default now(),
    primary key (item_name, item_type, summary_from, summary_to)
);

create table if not exists public.ai_insight_logs (
    id uuid primary key default gen_random_uuid(),
    provider text not null default 'mock',
    insight_type text not null,
    input_metrics jsonb not null default '{}'::jsonb,
    insight_text text not null,
    created_by uuid references public.app_users(id) on delete set null,
    created_at timestamptz not null default now()
);

create table if not exists public.forecast_results (
    id uuid primary key default gen_random_uuid(),
    forecast_date date not null,
    forecast_type text not null default 'daily_demand',
    predicted_orders numeric not null default 0,
    predicted_revenue numeric not null default 0,
    method text not null default 'rule_based_7_day_average',
    factors jsonb not null default '{}'::jsonb,
    created_by uuid references public.app_users(id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_ai_insight_logs_created_at
    on public.ai_insight_logs (created_at desc);
create index if not exists idx_forecast_results_date
    on public.forecast_results (forecast_date, forecast_type);
