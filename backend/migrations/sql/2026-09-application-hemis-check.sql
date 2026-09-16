-- Automated HEMIS existence check: does this applicant already exist as an
-- enrolled student in HEMIS (student.xiuedu.uz), matched by passport PIN +
-- number. Filled by the "HEMIS sinxron" background job. Idempotent.
--   auto_hemis_check: 'topildi' | 'topilmadi' | NULL (not checked / no passport data)

ALTER TABLE applications ADD COLUMN IF NOT EXISTS auto_hemis_check VARCHAR(20);
ALTER TABLE applications ADD COLUMN IF NOT EXISTS hemis_checked_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_applications_auto_hemis_check ON applications (auto_hemis_check);
