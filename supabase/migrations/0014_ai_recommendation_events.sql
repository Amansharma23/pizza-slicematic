-- SliceMatic Stage AI - Recommendation event tracking
-- Track accepted/rejected AI upsells and coupon recommendations.

create extension if not exists pgcrypto;

create table if not exists public.ai_recommendation_events (
    id uuid primary key default gen_random_uuid(),
    recommendation_type text not null
        check (recommendation_type in ('upsell', 'coupon', 'inventory', 'staff', 'churn')),
    recommendation_key text not null,
    title text not null,
    detail text,
    status text not null
        check (status in ('presented', 'accepted', 'rejected')),
    estimated_value numeric not null default 0,
    source_metrics jsonb not null default '{}'::jsonb,
    related_entity_type text,
    related_entity_id text,
    created_by uuid,
    created_at timestamptz not null default now()
);

create index if not exists idx_ai_recommendation_events_type_status
    on public.ai_recommendation_events (recommendation_type, status, created_at desc);

create index if not exists idx_ai_recommendation_events_key
    on public.ai_recommendation_events (recommendation_key, created_at desc);
