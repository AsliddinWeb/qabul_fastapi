-- 03: Programs v2 — Branch + EducationLevel + EducationForm + new Program shape
-- DROPS old faculties / admission_periods / program_offerings (after data salvage)
BEGIN;

-- ----- new branch / level / form tables -----
CREATE TABLE IF NOT EXISTS branches (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS education_levels (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS education_forms (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed common values
INSERT INTO education_levels (name)
VALUES ('Bakalavr'), ('Magistr')
ON CONFLICT (name) DO NOTHING;

INSERT INTO education_forms (name)
VALUES ('Kunduzgi'), ('Sirtqi'), ('Kechki'), ('Masofaviy')
ON CONFLICT (name) DO NOTHING;

INSERT INTO branches (name)
VALUES ('Toshkent'), ('Andijon'), ('Nukus')
ON CONFLICT (name) DO NOTHING;

-- ----- DROP old programs/offerings/periods/faculties (clean slate, no historical data to preserve) -----
-- Drop in FK-safe order: applications.program_offering_id (will be replaced in step 06), then offerings, periods, programs, faculties.
ALTER TABLE IF EXISTS applications
    DROP COLUMN IF EXISTS program_offering_id;

DROP TABLE IF EXISTS program_offerings CASCADE;
DROP TABLE IF EXISTS admission_periods CASCADE;
DROP TABLE IF EXISTS programs CASCADE;
DROP TABLE IF EXISTS faculties CASCADE;

-- ----- new programs table (matching old Django shape) -----
CREATE TABLE programs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id            UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    education_level_id   UUID NOT NULL REFERENCES education_levels(id) ON DELETE RESTRICT,
    education_form_id    UUID NOT NULL REFERENCES education_forms(id) ON DELETE RESTRICT,
    name                 VARCHAR(200) NOT NULL,
    code                 VARCHAR(100) NOT NULL,
    image_id             UUID REFERENCES files(id) ON DELETE SET NULL,
    tuition_fee          VARCHAR(255) NOT NULL,
    study_duration       VARCHAR(100) NOT NULL,
    contract_series      VARCHAR(100) NOT NULL,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_programs_branch_id           ON programs(branch_id);
CREATE INDEX ix_programs_education_level_id  ON programs(education_level_id);
CREATE INDEX ix_programs_education_form_id   ON programs(education_form_id);
CREATE INDEX ix_programs_is_active           ON programs(is_active);

COMMIT;
