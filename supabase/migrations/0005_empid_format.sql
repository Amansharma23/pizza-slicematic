-- SliceMatic — employee IDs use the brand format SMEMP001 (was EMP-001).
-- Run in the Supabase SQL editor (after 0004). Idempotent.
--
-- Only the trigger function changes; existing rows are untouched (none exist
-- yet outside seeds, which pass explicit SMEMP ids anyway).

create or replace function public.assign_emp_id()
returns trigger
language plpgsql
as $$
begin
    if new.role in ('staff', 'kitchen_staff', 'delivery') and new.emp_id is null then
        new.emp_id := 'SMEMP' || lpad(nextval('public.emp_id_seq')::text, 3, '0');
    end if;
    return new;
end;
$$;
