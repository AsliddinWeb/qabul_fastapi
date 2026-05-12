-- audit_logs DDL ships with two broken defaults that silently lose rows
-- from the HTTP audit middleware:
--   * `id` has no DEFAULT but is NOT NULL — Core insert(...).values(...)
--     without an explicit id fails the constraint.
--   * `created_at` has a frozen-timestamp default ('2026-04-27 13:24:...')
--     from the schema dump, so rows that don't set it explicitly all carry
--     the same fake timestamp.
--
-- The middleware now provides id/created_at explicitly (commit alongside
-- this migration), but we also patch the DDL so an accidental Core insert
-- elsewhere — or anyone running raw SQL — gets sensible behaviour.
--
-- Idempotent.

-- audit_logs.id → uuid_generate_v4() (pgcrypto is also fine, but the
-- existing schema already uses uuid_generate_v4 in other tables).
ALTER TABLE audit_logs
    ALTER COLUMN id SET DEFAULT uuid_generate_v4();

-- audit_logs.created_at → now()
ALTER TABLE audit_logs
    ALTER COLUMN created_at SET DEFAULT now();
