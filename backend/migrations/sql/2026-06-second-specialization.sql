-- 2-mutaxassislik (second specialization) admission type.
-- Run AFTER deploying code that adds the SECOND_SPEC enum + the
-- is_for_second_specialization column. The application boot will
-- otherwise crash trying to coerce the new enum value.
--
-- Idempotent: each statement guards on existence so re-running on a
-- partially-migrated database is safe.

BEGIN;

-- ============================================================
-- 1) Extend the admission_type enum.
--    PG quirk: ALTER TYPE … ADD VALUE has to live OUTSIDE a tx for
--    immediate-use semantics. We add it OUTSIDE this block so the
--    enum value is committed before anything depends on it.
-- ============================================================
COMMIT;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        JOIN pg_type ON pg_type.oid = pg_enum.enumtypid
        WHERE pg_type.typname = 'admission_type'
          AND pg_enum.enumlabel = 'ikkinchi_mutaxassislik'
    ) THEN
        ALTER TYPE admission_type ADD VALUE 'ikkinchi_mutaxassislik';
    END IF;
END $$;

BEGIN;

-- ============================================================
-- 2) Diplom.is_for_second_specialization
--    Default FALSE so every existing row stays a "1-kurs diplomi"
--    (which is what they were created for). NEW rows for the
--    2-mutaxassislik flow set it TRUE explicitly.
-- ============================================================
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'diploms'
          AND column_name = 'is_for_second_specialization'
    ) THEN
        ALTER TABLE diploms
            ADD COLUMN is_for_second_specialization BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- ============================================================
-- 3) Replace the old unique with a composite one so each user can
--    have BOTH a 1-kurs diplom AND a 2-mutaxassislik diplom.
-- ============================================================
ALTER TABLE diploms DROP CONSTRAINT IF EXISTS uq_diploms_user_id;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_diploms_user_purpose'
    ) THEN
        ALTER TABLE diploms
            ADD CONSTRAINT uq_diploms_user_purpose
            UNIQUE (user_id, is_for_second_specialization);
    END IF;
END $$;

COMMIT;
