-- HEMIS enrolment state per application, toggled from the Telegram bot's
-- ✅/❌ buttons. New applications default to 'qoshilmadi' (not yet in HEMIS).
-- Idempotent: safe to re-run.

ALTER TABLE applications ADD COLUMN IF NOT EXISTS hemis_status VARCHAR(20) NOT NULL DEFAULT 'qoshilmadi';
ALTER TABLE applications ADD COLUMN IF NOT EXISTS hemis_marked_by VARCHAR(150);
ALTER TABLE applications ADD COLUMN IF NOT EXISTS hemis_marked_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_applications_hemis_status ON applications (hemis_status);
