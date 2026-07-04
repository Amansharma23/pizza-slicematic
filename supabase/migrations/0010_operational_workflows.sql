-- SliceMatic Stage 3B - Operational workflow completion
-- Small compatibility additions for admin decisions and request tracking.

alter table public.inventory_requests
    add column if not exists updated_at timestamptz not null default now();

create index if not exists idx_inventory_requests_status
    on public.inventory_requests (status, created_at desc);
