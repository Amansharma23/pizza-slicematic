-- SliceMatic Stage AI - Customer feedback sentiment source
-- Stores customer reviews/feedback for deterministic Admin AI sentiment scoring.

create extension if not exists pgcrypto;

create table if not exists public.customer_feedback (
    id uuid primary key default gen_random_uuid(),
    order_id uuid,
    customer_name text,
    customer_phone text,
    channel text not null default 'manual'
        check (channel in ('manual', 'app', 'web', 'whatsapp', 'voice', 'google', 'zomato', 'swiggy')),
    rating int not null check (rating between 1 and 5),
    feedback_text text not null,
    sentiment_label text not null default 'neutral'
        check (sentiment_label in ('positive', 'neutral', 'negative')),
    sentiment_score numeric not null default 0,
    topics jsonb not null default '[]'::jsonb,
    source_metadata jsonb not null default '{}'::jsonb,
    created_by uuid,
    created_at timestamptz not null default now()
);

create index if not exists idx_customer_feedback_created_at
    on public.customer_feedback (created_at desc);

create index if not exists idx_customer_feedback_sentiment
    on public.customer_feedback (sentiment_label, created_at desc);

create index if not exists idx_customer_feedback_order
    on public.customer_feedback (order_id);
