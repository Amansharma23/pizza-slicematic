-- SliceMatic Stage 3 - Sync app_users columns
-- Automatically synchronises the redundant name/full_name and secret_hash/password_hash columns
-- so both Customer Auth and Admin Panel operate seamlessly on the same table.

create or replace function public.sync_user_names_and_hashes()
returns trigger
language plpgsql
as $$
begin
    -- Sync name and full_name
    if new.name is null and new.full_name is not null then
        new.name := new.full_name;
    elsif new.full_name is null and new.name is not null then
        new.full_name := new.name;
    end if;

    -- Sync secret_hash and password_hash
    if new.secret_hash is null and new.password_hash is not null then
        new.secret_hash := new.password_hash;
    elsif new.password_hash is null and new.secret_hash is not null then
        new.password_hash := new.secret_hash;
    end if;

    return new;
end;
$$;

drop trigger if exists trg_sync_user_names_and_hashes on public.app_users;
create trigger trg_sync_user_names_and_hashes
    before insert or update on public.app_users
    for each row execute function public.sync_user_names_and_hashes();
