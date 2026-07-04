-- SliceMatic Stage 3 - Staff CRUD and coupon campaigns

alter table public.discount_rules
    add column if not exists coupon_code text unique;

alter table public.discount_rules
    add column if not exists description text;

insert into public.permissions (code, description) values
    ('discounts.manage', 'Manage discount rules and coupon campaigns.')
on conflict (code) do update set description = excluded.description;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
join public.permissions p on p.code = 'discounts.manage'
where r.name in ('Admin', 'Manager')
on conflict do nothing;
