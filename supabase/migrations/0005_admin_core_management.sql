-- SliceMatic Stage 3 - Admin core management
-- Menu, pricing settings, discount rules, staff profiles, and audit seeds.

create extension if not exists pgcrypto;

create table if not exists public.menu_categories (
    id         uuid primary key default gen_random_uuid(),
    code       text not null unique,
    name       text not null,
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists public.menu_items (
    id          uuid primary key default gen_random_uuid(),
    item_code   text not null unique,
    category_id uuid not null references public.menu_categories(id),
    name        text not null,
    price       numeric not null check (price >= 0),
    is_available boolean not null default true,
    is_deleted   boolean not null default false,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create table if not exists public.price_history (
    id          uuid primary key default gen_random_uuid(),
    menu_item_id uuid not null references public.menu_items(id) on delete cascade,
    old_price   numeric,
    new_price   numeric not null check (new_price >= 0),
    changed_by  uuid references public.app_users(id) on delete set null,
    changed_at  timestamptz not null default now(),
    reason      text
);

create table if not exists public.app_settings (
    key        text primary key,
    value      jsonb not null,
    updated_by uuid references public.app_users(id) on delete set null,
    updated_at timestamptz not null default now()
);

create table if not exists public.discount_rules (
    id               uuid primary key default gen_random_uuid(),
    name             text not null,
    discount_percent numeric not null check (discount_percent >= 0 and discount_percent <= 100),
    threshold_amount numeric not null default 0 check (threshold_amount >= 0),
    start_date       date,
    end_date         date,
    is_active        boolean not null default true,
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now(),
    check (start_date is null or end_date is null or start_date <= end_date)
);

create table if not exists public.staff_profiles (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null unique references public.app_users(id) on delete cascade,
    role_name   text not null,
    employee_code text unique,
    is_active  boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_menu_items_category on public.menu_items (category_id);
create index if not exists idx_menu_items_available on public.menu_items (is_available, is_deleted);
create index if not exists idx_discount_rules_active on public.discount_rules (is_active);

insert into public.menu_categories (code, name, sort_order) values
    ('base', 'Pizza Bases', 1),
    ('pizza', 'Pizzas', 2),
    ('topping', 'Toppings', 3)
on conflict (code) do update set name = excluded.name, sort_order = excluded.sort_order;

insert into public.menu_items (item_code, category_id, name, price)
select v.item_code, c.id, v.name, v.price
from (
    values
    ('B1', 'base', 'Thin Crust', 149),
    ('B2', 'base', 'Thick Crust', 179),
    ('B3', 'base', 'Cheese Burst', 229),
    ('B4', 'base', 'Whole Wheat', 159),
    ('B5', 'base', 'Multigrain', 169),
    ('P1', 'pizza', 'Margherita', 299),
    ('P2', 'pizza', 'Chicago Deep Dish', 349),
    ('P3', 'pizza', 'Greek Mediterranean', 329),
    ('P4', 'pizza', 'California Veggie', 339),
    ('P5', 'pizza', 'Farm House', 319),
    ('P6', 'pizza', 'Pepperoni Classic', 369),
    ('P7', 'pizza', 'BBQ Chicken', 379),
    ('P8', 'pizza', 'Paneer Tikka', 349),
    ('T1', 'topping', 'Black Olives', 49),
    ('T2', 'topping', 'Extra Cheese', 69),
    ('T3', 'topping', 'Button Mushrooms', 49),
    ('T4', 'topping', 'Green Peppers', 39),
    ('T5', 'topping', 'Jalapenos', 39),
    ('T6', 'topping', 'Sun-Dried Tomatoes', 59),
    ('T7', 'topping', 'Caramelised Onions', 49),
    ('T8', 'topping', 'Sweet Corn', 39),
    ('T9', 'topping', 'Roasted Garlic', 49),
    ('T10', 'topping', 'Peri-Peri Drizzle', 59)
) as v(item_code, category_code, name, price)
join public.menu_categories c on c.code = v.category_code
on conflict (item_code) do update set
    name = excluded.name,
    price = excluded.price,
    updated_at = now();

insert into public.app_settings (key, value) values
    ('gst_rate_percent', '{"value": 18}'),
    ('discount_rate_percent', '{"value": 10}'),
    ('discount_quantity_threshold', '{"value": 5}')
on conflict (key) do nothing;

insert into public.discount_rules (
    name, discount_percent, threshold_amount, start_date, end_date, is_active
)
values ('Bulk quantity discount', 10, 5, current_date, null, true)
on conflict do nothing;

insert into public.staff_profiles (user_id, role_name, employee_code, is_active)
select u.id, 'Admin', 'ADM-001', true
from public.app_users u
where u.email = 'admin@slicematic.local'
on conflict (user_id) do update set
    role_name = excluded.role_name,
    employee_code = excluded.employee_code,
    is_active = excluded.is_active,
    updated_at = now();
