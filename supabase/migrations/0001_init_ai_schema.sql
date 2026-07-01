-- SliceMatic — Stage 3 AI layer schema
-- Run in the Supabase SQL editor (or `supabase db push`).
--
-- Design notes:
--   * `orders` mirrors orders_log.txt field-for-field, plus AI/source metadata.
--     The .txt log remains the primary, graded output; this table is an additive
--     parallel write. A Supabase failure must never break the .txt write.
--   * `sessions` = one row per chat/voice conversation.
--   * `messages` = chat history + voice transcripts in one table (one row/turn).
--   * Idempotent: safe to re-run.

-- gen_random_uuid() lives in pgcrypto (preinstalled on Supabase).
create extension if not exists pgcrypto;

-- --------------------------------------------------------------------------- --
-- sessions
-- --------------------------------------------------------------------------- --
create table if not exists public.sessions (
    id               text primary key,                 -- frontend-supplied session_id
    channel          text not null default 'chat'   check (channel  in ('chat','voice')),
    language         text not null default 'en'     check (language in ('en','hi')),
    customer_name    text,
    customer_phone   text,
    status           text not null default 'active' check (status   in ('active','ordered','abandoned','escalated')),
    human_escalated  boolean not null default false,
    voice_started_at timestamptz,                       -- for the 3-minute voice cap
    metadata         jsonb not null default '{}'::jsonb,-- extracted fields, misc
    started_at       timestamptz not null default now(),
    last_activity_at timestamptz not null default now(),
    ended_at         timestamptz
);

create index if not exists idx_sessions_last_activity on public.sessions (last_activity_at desc);

-- --------------------------------------------------------------------------- --
-- messages  (chat history AND voice transcripts)
-- --------------------------------------------------------------------------- --
create table if not exists public.messages (
    id                uuid primary key default gen_random_uuid(),
    session_id        text not null references public.sessions(id) on delete cascade,
    role              text not null check (role in ('user','assistant','tool','system')),
    content           text,
    channel           text check (channel in ('chat','voice')),
    model_used        text,        -- which OpenRouter model produced an assistant turn
    tool_name         text,        -- for role = 'tool' result rows
    tool_calls        jsonb,       -- tool calls requested by an assistant turn
    prompt_tokens     int,
    completion_tokens int,
    audio_duration_ms int,         -- voice: length of the audio turn
    stt_confidence    numeric,     -- voice: Deepgram transcript confidence
    created_at        timestamptz not null default now()
);

create index if not exists idx_messages_session on public.messages (session_id, created_at);

-- --------------------------------------------------------------------------- --
-- orders  (mirror of orders_log.txt + AI metadata)
-- --------------------------------------------------------------------------- --
create table if not exists public.orders (
    id             uuid primary key default gen_random_uuid(),
    order_no       text unique,                          -- e.g. SM-20260629-0042
    session_id     text references public.sessions(id) on delete set null,
    source         text not null default 'gradio' check (source in ('gradio','chat','voice','api')),

    -- customer
    customer_name  text not null,
    customer_phone text not null,

    -- the line/config (mirrors the log's flat fields, from one Bill)
    base_name      text not null,
    pizza_name     text not null,
    topping_name   text not null,
    unit_price     numeric not null,
    quantity       int     not null,

    -- money (computed only by core/pricing.py)
    subtotal       numeric not null,
    discount       numeric not null default 0,
    gst            numeric not null,
    total          numeric not null,

    payment_mode   text not null,

    -- optional: multi-line AI orders keep their full breakdown here
    items          jsonb,
    language       text,
    status         text not null default 'received' check (status in ('received','confirmed','cancelled')),

    logged_at      text,                                 -- the orders_log.txt timestamp string, for cross-ref
    created_at     timestamptz not null default now()
);

create index if not exists idx_orders_created_at on public.orders (created_at desc);
create index if not exists idx_orders_source     on public.orders (source);
