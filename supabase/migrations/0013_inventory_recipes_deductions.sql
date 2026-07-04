-- SliceMatic Stage 6C - Inventory recipes and automatic stock deductions
-- Map menu items to ingredients and record per-order deductions once.

create extension if not exists pgcrypto;

create table if not exists public.menu_item_ingredients (
    id uuid primary key default gen_random_uuid(),
    menu_item_id uuid not null references public.menu_items(id) on delete cascade,
    ingredient_id uuid not null references public.ingredients(id) on delete cascade,
    quantity_per_unit numeric not null check (quantity_per_unit > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (menu_item_id, ingredient_id)
);

create table if not exists public.order_inventory_deductions (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references public.orders(id) on delete cascade,
    ingredient_id uuid not null references public.ingredients(id) on delete cascade,
    quantity numeric not null check (quantity > 0),
    stock_transaction_id uuid references public.stock_transactions(id) on delete set null,
    deducted_by uuid references public.app_users(id) on delete set null,
    deducted_at timestamptz not null default now(),
    unique (order_id, ingredient_id)
);

create index if not exists idx_menu_item_ingredients_item
    on public.menu_item_ingredients (menu_item_id);
create index if not exists idx_order_inventory_deductions_order
    on public.order_inventory_deductions (order_id);

insert into public.menu_item_ingredients (
    menu_item_id, ingredient_id, quantity_per_unit
)
select mi.id, i.id, v.quantity_per_unit
from (
    values
    ('B1', 'Thin Crust Base', 1),
    ('B2', 'Thin Crust Base', 1),
    ('B3', 'Thin Crust Base', 1),
    ('B4', 'Thin Crust Base', 1),
    ('B5', 'Thin Crust Base', 1),
    ('P1', 'Mozzarella Cheese', 0.12),
    ('P1', 'Pizza Sauce', 0.08),
    ('P2', 'Mozzarella Cheese', 0.16),
    ('P2', 'Pizza Sauce', 0.1),
    ('P3', 'Mozzarella Cheese', 0.12),
    ('P3', 'Pizza Sauce', 0.08),
    ('P4', 'Mozzarella Cheese', 0.12),
    ('P4', 'Pizza Sauce', 0.08),
    ('P5', 'Mozzarella Cheese', 0.12),
    ('P5', 'Pizza Sauce', 0.08),
    ('P6', 'Mozzarella Cheese', 0.14),
    ('P6', 'Pizza Sauce', 0.08),
    ('P7', 'Chicken Tikka', 0.18),
    ('P7', 'Mozzarella Cheese', 0.1),
    ('P8', 'Paneer Cubes', 0.16),
    ('P8', 'Mozzarella Cheese', 0.1),
    ('T2', 'Mozzarella Cheese', 0.05),
    ('T8', 'Sweet Corn', 0.04)
) as v(item_code, ingredient_name, quantity_per_unit)
join public.menu_items mi on mi.item_code = v.item_code
join public.ingredients i on i.name = v.ingredient_name
on conflict (menu_item_id, ingredient_id) do update set
    quantity_per_unit = excluded.quantity_per_unit,
    updated_at = now();
