-- SliceMatic Stage 6A - Staff kitchen surface
-- Staff-specific permissions and local backstage staff seed.

create extension if not exists pgcrypto;

insert into public.permissions (code, description) values
    ('staff.kitchen.access', 'Access the staff kitchen surface.'),
    ('inventory.request', 'Create stock replenishment requests.')
on conflict (code) do update set description = excluded.description;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
join public.permissions p on p.code in (
    'staff.kitchen.access',
    'orders.read',
    'orders.update_status',
    'inventory.request'
)
where r.name = 'Backstage Staff'
on conflict do nothing;

insert into public.app_users (email, full_name, phone, status)
values (
    'kitchen@slicematic.local',
    'Kitchen Staff',
    '9876500001',
    'active'
)
on conflict (email) do update set
    full_name = excluded.full_name,
    phone = excluded.phone,
    status = excluded.status,
    updated_at = now();

insert into public.user_roles (user_id, role_id)
select u.id, r.id
from public.app_users u
join public.roles r on r.name = 'Backstage Staff'
where u.email = 'kitchen@slicematic.local'
on conflict do nothing;

insert into public.staff_profiles (user_id, role_name, employee_code, is_active)
select u.id, 'Backstage Staff', 'KIT-001', true
from public.app_users u
where u.email = 'kitchen@slicematic.local'
on conflict (user_id) do update set
    role_name = excluded.role_name,
    employee_code = excluded.employee_code,
    is_active = excluded.is_active,
    updated_at = now();
