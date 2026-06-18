-- Applicant CRM-style contact_status field.
-- Idempotent: enum + column + index guarded on existence.
-- Run AFTER deploying the code that knows about the enum value.

-- 1) Enum type
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'applicant_contact_status'
    ) THEN
        CREATE TYPE applicant_contact_status AS ENUM (
            'new', 'contacted', 'interested', 'lost', 'enrolled'
        );
    END IF;
END $$;

-- 2) Column on applicants
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'applicants' AND column_name = 'contact_status'
    ) THEN
        ALTER TABLE applicants
            ADD COLUMN contact_status applicant_contact_status
            NOT NULL DEFAULT 'new';
    END IF;
END $$;

-- 3) Index — the applicants list filters by this column.
CREATE INDEX IF NOT EXISTS ix_applicants_contact_status
    ON applicants (contact_status);

-- 4) Backfill: any applicant who already has a SIGNED contract should
--    land on 'enrolled' instead of staying at the 'new' default —
--    otherwise the freshly-added column looks empty / misleading for
--    every existing record. Idempotent (matches only 'new' rows).
UPDATE applicants a
   SET contact_status = 'enrolled'
 WHERE a.contact_status = 'new'
   AND EXISTS (
       SELECT 1 FROM contracts c
       JOIN applications ap ON ap.id = c.application_id
       WHERE ap.applicant_id = a.id
         AND c.status = 'signed'
   );
