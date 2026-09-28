-- NightCopy: private, user-scoped storage. Run in your ColeTech Supabase SQL editor.
begin;
insert into storage.buckets (id,name,public,file_size_limit)
values ('nightcopy','nightcopy',false,52428800)
on conflict (id) do update set public=false, file_size_limit=52428800;

drop policy if exists "nightcopy_owner_read" on storage.objects;
create policy "nightcopy_owner_read" on storage.objects for select to authenticated
using (bucket_id='nightcopy' and (storage.foldername(name))[1]=(select auth.uid()::text));
drop policy if exists "nightcopy_owner_insert" on storage.objects;
create policy "nightcopy_owner_insert" on storage.objects for insert to authenticated
with check (bucket_id='nightcopy' and (storage.foldername(name))[1]=(select auth.uid()::text));
-- No overwrite or delete policies. The interface creates new copy names on conflict.

create table if not exists public.nightcopy_transfers (
 id uuid primary key,
 user_id uuid not null references auth.users(id) on delete cascade,
 operation text not null check (operation in ('transfer','duplicate','download','zip')),
 source text not null,
 destination text not null,
 file_count integer not null check (file_count>=0),
 bytes bigint not null check (bytes>=0),
 status text not null check (status='complete'),
 created_at timestamptz not null default now(),
 completed_at timestamptz not null
);
alter table public.nightcopy_transfers enable row level security;
create index if not exists nightcopy_transfers_user_created on public.nightcopy_transfers(user_id,created_at desc);
grant select,insert on public.nightcopy_transfers to authenticated;
revoke all on public.nightcopy_transfers from anon;
drop policy if exists "nightcopy_transfer_owner_read" on public.nightcopy_transfers;
create policy "nightcopy_transfer_owner_read" on public.nightcopy_transfers for select to authenticated using (user_id=(select auth.uid()));
drop policy if exists "nightcopy_transfer_owner_insert" on public.nightcopy_transfers;
create policy "nightcopy_transfer_owner_insert" on public.nightcopy_transfers for insert to authenticated with check (user_id=(select auth.uid()));
commit;
