-- Optional free-text comment attached to a HEMIS decision (from the panel or
-- the Telegram bot's ✅/❌ flow). Idempotent: safe to re-run.

ALTER TABLE applications ADD COLUMN IF NOT EXISTS hemis_comment TEXT;
