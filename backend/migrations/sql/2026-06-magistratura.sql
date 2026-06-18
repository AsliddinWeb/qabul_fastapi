-- Add 'magistratura' to the admission_type enum.
-- Idempotent: guarded on pg_enum existence.
--
-- Run AFTER deploying the code that knows about the enum value.
-- Magistratura applications target only "Magistr"-level programs,
-- kunduzgi form, and reuse the Bakalavr diplom row
-- (is_for_second_specialization=true) created for the
-- 2-mutaxassislik flow. No table changes needed beyond the enum.

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        JOIN pg_type ON pg_type.oid = pg_enum.enumtypid
        WHERE pg_type.typname = 'admission_type'
          AND pg_enum.enumlabel = 'magistratura'
    ) THEN
        ALTER TYPE admission_type ADD VALUE 'magistratura';
    END IF;
END $$;
