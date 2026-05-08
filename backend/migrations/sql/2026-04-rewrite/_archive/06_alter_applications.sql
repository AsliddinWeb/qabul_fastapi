-- 06: Reshape applications — admission_type enum, branch/level/form/program FKs,
-- diplom + transfer_diplom + course FKs, contract_file_id; rewrite status enum.
BEGIN;

-- ---- Old data: applications referencing dropped program_offerings.
-- Step 03 already dropped applications.program_offering_id.
-- We additionally truncate any orphaned application rows since FKs to programs are about to change.
TRUNCATE TABLE application_status_history CASCADE;
TRUNCATE TABLE applications CASCADE;

-- ---- Drop old constraints we don't need
ALTER TABLE applications DROP CONSTRAINT IF EXISTS uq_applications_applicant_id_program_offering_id;

-- ---- AdmissionType enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'admission_type') THEN
        CREATE TYPE admission_type AS ENUM ('yangi_qabul', 'perevod');
    END IF;
END$$;

-- ---- ApplicationStatus enum: drop and recreate with Uzbek values
-- (TRUNCATEd above, so no live rows reference the old values)

-- Need to drop dependent columns first so we can drop the enum type
ALTER TABLE applications DROP COLUMN IF EXISTS status;
ALTER TABLE application_status_history DROP COLUMN IF EXISTS from_status;
ALTER TABLE application_status_history DROP COLUMN IF EXISTS to_status;

DROP TYPE IF EXISTS application_status;
CREATE TYPE application_status AS ENUM (
    'topshirildi',
    'korib_chiqilmoqda',
    'qabul_qilindi',
    'rad_etildi'
);

-- ---- Add new application columns
ALTER TABLE applications
    ADD COLUMN IF NOT EXISTS admission_type admission_type NOT NULL DEFAULT 'yangi_qabul',
    ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS education_level_id UUID REFERENCES education_levels(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS education_form_id UUID REFERENCES education_forms(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS program_id UUID REFERENCES programs(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS diplom_id UUID REFERENCES diploms(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS transfer_diplom_id UUID REFERENCES transfer_diploms(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS contract_file_id UUID REFERENCES files(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS status application_status NOT NULL DEFAULT 'topshirildi';

-- After branch_id / education_*_id / program_id are populated, switch to NOT NULL
-- (currently nullable for empty table OK).

ALTER TABLE applications ALTER COLUMN branch_id SET NOT NULL;
ALTER TABLE applications ALTER COLUMN education_level_id SET NOT NULL;
ALTER TABLE applications ALTER COLUMN education_form_id SET NOT NULL;
ALTER TABLE applications ALTER COLUMN program_id SET NOT NULL;

-- Indexes
CREATE INDEX IF NOT EXISTS ix_applications_admission_type ON applications(admission_type);
CREATE INDEX IF NOT EXISTS ix_applications_branch_id ON applications(branch_id);
CREATE INDEX IF NOT EXISTS ix_applications_program_id ON applications(program_id);
CREATE INDEX IF NOT EXISTS ix_applications_status ON applications(status);

-- New uniqueness: one application per (applicant, program)
ALTER TABLE applications
    ADD CONSTRAINT uq_applications_applicant_program UNIQUE (applicant_id, program_id);

-- Status history: re-add columns with new enum
ALTER TABLE application_status_history
    ADD COLUMN from_status application_status,
    ADD COLUMN to_status application_status NOT NULL;

COMMIT;
