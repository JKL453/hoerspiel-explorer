# Supabase full refresh runbook

This runbook replaces the seven product tables from `cleaned_details.json`.
It deliberately preserves `scrape_targets` and `episode_targets`.

## 1. Create and verify the backup

Run this once in the Supabase SQL Editor. Change the schema suffix if that
backup name already exists.

```sql
begin;

create schema reload_backup_20260807;

create table reload_backup_20260807.series
as table public.series;
create table reload_backup_20260807.episodes
as table public.episodes;
create table reload_backup_20260807.speakers
as table public.speakers;
create table reload_backup_20260807.roles
as table public.roles;
create table reload_backup_20260807.genres
as table public.genres;
create table reload_backup_20260807.episode_speakers
as table public.episode_speakers;
create table reload_backup_20260807.episode_genres
as table public.episode_genres;

commit;
```

Verify that backup and production counts match:

```sql
select 'series' as table_name,
       (select count(*) from public.series) as production,
       (select count(*) from reload_backup_20260807.series) as backup
union all
select 'episodes',
       (select count(*) from public.episodes),
       (select count(*) from reload_backup_20260807.episodes)
union all
select 'speakers',
       (select count(*) from public.speakers),
       (select count(*) from reload_backup_20260807.speakers)
union all
select 'roles',
       (select count(*) from public.roles),
       (select count(*) from reload_backup_20260807.roles)
union all
select 'genres',
       (select count(*) from public.genres),
       (select count(*) from reload_backup_20260807.genres)
union all
select 'episode_speakers',
       (select count(*) from public.episode_speakers),
       (select count(*) from reload_backup_20260807.episode_speakers)
union all
select 'episode_genres',
       (select count(*) from public.episode_genres),
       (select count(*) from reload_backup_20260807.episode_genres);
```

Do not continue unless every pair of counts matches.

## 2. Empty only the product tables

```sql
begin;

truncate table
    public.episode_speakers,
    public.episode_genres,
    public.episodes,
    public.speakers,
    public.roles,
    public.genres,
    public.series
restart identity cascade;

commit;
```

Confirm that all seven tables are empty. Do not truncate `scrape_targets` or
`episode_targets`.

## 3. Add the stable episode key

Run `src/hoerspiel_discovery/sql/05_source_key.sql` in the SQL Editor. The
migration aborts unless `episodes` is empty.

## 4. Rebuild and load

1. Redeploy and run `build-cleaned-details` so every record receives a unique
   `source_key`.
2. Check the Prefect validation summary.
3. Deploy and run `load-cleaned-details` without parameters.
4. Keep the backup schema until relational validation, spot checks, and the
   later embedding run have succeeded.

The loader refuses to start if any product table is nonempty. If it fails
partway through, repeat the truncate and restart the whole loader.

## 5. Rollback

To restore the exact previous state, empty the seven product tables, remove the
new `source_key` column, and insert the backup tables in dependency order:
dimensions first, then episodes, then both junction tables. Keep the backup
schema until this rollback is no longer needed.
