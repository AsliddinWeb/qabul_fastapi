-- Per-user permission revocation list.
--
-- Admin can switch off specific permissions for a single user that their role
-- would otherwise grant (e.g. an operator without contracts.sign). The
-- require_permission dep consults this list after the role-permission matrix.
-- A NULL/empty array means "use whatever the role grants" (default).

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS permissions_revoked JSONB NOT NULL DEFAULT '[]';
