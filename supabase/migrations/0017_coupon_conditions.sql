-- SliceMatic Admin UX - coupon quantity/value conditions

create table if not exists public.discount_rule_conditions (
    discount_rule_id uuid primary key,
    min_quantity int,
    no_min_quantity boolean not null default true,
    no_min_value boolean not null default false,
    updated_at timestamptz not null default now()
);
