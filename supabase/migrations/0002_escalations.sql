-- SliceMatic — Stage 3: escalations admin queue
-- Run in the Supabase SQL editor (after 0001). Idempotent.
--
-- One row per "talk to a human" event. Admins triage from here:
--   * the conversation transcript:  messages WHERE session_id = <session_id>
--   * the LLM-level trace:          langfuse_url (or search Langfuse by langfuse_session_id)

create table if not exists public.escalations (
    id                  uuid primary key default gen_random_uuid(),
    session_id          text references public.sessions(id) on delete cascade,
    reason              text,
    status              text not null default 'open' check (status in ('open', 'resolved')),

    -- snapshot for a quick admin view (denormalised from the session)
    channel             text,
    language            text,
    customer_name       text,
    customer_phone      text,

    -- links to the full context
    langfuse_session_id text,
    langfuse_url        text,

    created_at          timestamptz not null default now(),
    resolved_at         timestamptz
);

create index if not exists idx_escalations_status
    on public.escalations (status, created_at desc);
