-- Backfill users.referral_code for accounts created AFTER 05_referrals.sql ran.
--
-- The original migration's UPDATE only touched rows that existed at the time,
-- and the user-creation path (auth.verify_otp → UserRepository.create) didn't
-- assign a code until the user opened their referrals page. As a result, every
-- applicant that signed up between then and now has referral_code = NULL, so
-- their personal share link never rendered in the admin UI.
--
-- This migration repeats the deterministic backfill from 05 for any remaining
-- NULL rows: UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 6)). The unique
-- index permits collisions only in the astronomically unlikely case that two
-- UUIDs share the first 6 hex chars — we ignore conflicts so the migration
-- stays idempotent and any such row will get a fresh random code on next user
-- mutation via the repository path.
--
-- Idempotent.

UPDATE users
SET referral_code = UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 6))
WHERE referral_code IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM users u2
      WHERE u2.referral_code = UPPER(SUBSTRING(REPLACE(users.id::text, '-', ''), 1, 6))
  );
