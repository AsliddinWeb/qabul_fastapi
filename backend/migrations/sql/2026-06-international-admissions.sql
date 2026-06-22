-- International admissions — separate funnel for non-resident applicants.
-- Adds the table, indexes, and FK constraints to files for the 3 uploads.
-- Idempotent: safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS international_applications (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

    ref_number           VARCHAR(40) NOT NULL UNIQUE,

    full_name            VARCHAR(255) NOT NULL,
    country              VARCHAR(60)  NOT NULL,
    passport_number      VARCHAR(60)  NOT NULL,
    birth_date           DATE         NOT NULL,

    phone                VARCHAR(40)  NOT NULL,
    email                VARCHAR(120) NOT NULL,

    program              VARCHAR(20)  NOT NULL,
    faculty_code         VARCHAR(20)  NOT NULL,
    faculty_text         VARCHAR(120) NOT NULL,

    passport_file_id     UUID REFERENCES files(id) ON DELETE SET NULL,
    diploma_file_id      UUID REFERENCES files(id) ON DELETE SET NULL,
    photo_file_id        UUID REFERENCES files(id) ON DELETE SET NULL,

    stage                INTEGER     NOT NULL DEFAULT 0,
    rejected             BOOLEAN     NOT NULL DEFAULT FALSE,
    rejection_reason     TEXT,

    notes                TEXT,

    submitter_ip         VARCHAR(45),
    submitter_user_agent VARCHAR(500),
    language             VARCHAR(5)
);

-- Hot path indexes:
--   - stage      → Kanban board column-grouping
--   - country    → filter chip
--   - passport   → duplicate-passport guard (lookups in last 24h)
--   - email      → operator search
--   - created_at → newest-first ordering on every list
CREATE INDEX IF NOT EXISTS ix_intl_apps_stage      ON international_applications (stage);
CREATE INDEX IF NOT EXISTS ix_intl_apps_country    ON international_applications (country);
CREATE INDEX IF NOT EXISTS ix_intl_apps_passport   ON international_applications (passport_number);
CREATE INDEX IF NOT EXISTS ix_intl_apps_email      ON international_applications (email);
CREATE INDEX IF NOT EXISTS ix_intl_apps_phone      ON international_applications (phone);
CREATE INDEX IF NOT EXISTS ix_intl_apps_rejected   ON international_applications (rejected);
CREATE INDEX IF NOT EXISTS ix_intl_apps_created_at ON international_applications (created_at DESC);

-- updated_at is set by the ORM's TimestampMixin (server_onupdate=now()).
-- No PG trigger needed.

COMMIT;
