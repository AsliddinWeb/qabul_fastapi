-- Operator lead-intake toggle.
-- Adds users.accepts_leads (default TRUE) and indexes it so the lead
-- round-robin's WHERE clause stays index-backed.
--
-- Idempotent — safe to re-run.

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'accepts_leads'
    ) THEN
        ALTER TABLE users
            ADD COLUMN accepts_leads BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_users_accepts_leads ON users (accepts_leads);
