-- Per-user GRANTED permissions — opt-in extras on top of the role
-- (counterpart of permissions_revoked). Whitelisted in code
-- (GRANTABLE_PERMISSIONS), e.g. "applications.view_all": an operator with it
-- sees ALL applicants/applications, not only the ones they registered.
-- Idempotent: safe to re-run.

ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions_granted JSONB NOT NULL DEFAULT '[]'::jsonb;
