-- SliceMatic Admin UX - sides category and coupon/festival helpers

insert into public.menu_categories (code, name, sort_order) values
    ('side', 'Sides', 4)
on conflict (code) do update set name = excluded.name, sort_order = excluded.sort_order;

insert into public.menu_items (item_code, category_id, name, price)
select v.item_code, c.id, v.name, v.price
from (
    values
    ('S1', 'side', 'Garlic Breadsticks', 129),
    ('S2', 'side', 'Peri Peri Fries', 149),
    ('S3', 'side', 'Cheese Dip', 39),
    ('S4', 'side', 'Jalapeno Dip', 39),
    ('S5', 'side', 'Chocolate Brownie', 119),
    ('S6', 'side', 'Coke 500ml', 59),
    ('S7', 'side', 'Sprite 500ml', 59),
    ('S8', 'side', 'Iced Tea', 89)
) as v(item_code, category_code, name, price)
join public.menu_categories c on c.code = v.category_code
on conflict (item_code) do update set
    name = excluded.name,
    price = excluded.price,
    is_deleted = false,
    updated_at = now();

create table if not exists public.indian_festival_calendar (
    id uuid primary key default gen_random_uuid(),
    festival_date date not null,
    name text not null,
    coupon_theme text not null,
    suggested_discount_percent numeric not null default 10,
    suggested_threshold_amount numeric not null default 499,
    created_at timestamptz not null default now(),
    unique (festival_date, name)
);

insert into public.indian_festival_calendar (
    festival_date, name, coupon_theme, suggested_discount_percent,
    suggested_threshold_amount
) values
    ('2026-01-14', 'Makar Sankranti', 'Family combo offer', 10, 599),
    ('2026-01-26', 'Republic Day', 'Tricolour pizza celebration', 12, 699),
    ('2026-03-04', 'Holi', 'Colourful party combo', 15, 799),
    ('2026-08-28', 'Raksha Bandhan', 'Sibling combo offer', 12, 699),
    ('2026-08-26', 'Onam', 'Festive family feast', 10, 799),
    ('2026-10-02', 'Gandhi Jayanti', 'Long weekend value offer', 10, 599),
    ('2026-10-20', 'Dussehra', 'Victory feast combo', 15, 799),
    ('2026-11-08', 'Diwali', 'Diwali party combo', 18, 999),
    ('2026-12-25', 'Christmas', 'Christmas celebration combo', 15, 899)
on conflict (festival_date, name) do update set
    coupon_theme = excluded.coupon_theme,
    suggested_discount_percent = excluded.suggested_discount_percent,
    suggested_threshold_amount = excluded.suggested_threshold_amount;
