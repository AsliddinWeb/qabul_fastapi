-- Track who signed and who cancelled each contract.
--
-- Until now ContractsService set status + signed_at on sign() and status on
-- cancel() but never stamped WHO. The admin detail page needs both, and the
-- audit log alone isn't enough (operators can't read it).
--
-- Idempotent.

ALTER TABLE contracts
    ADD COLUMN IF NOT EXISTS signed_by_id UUID NULL REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE contracts
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ NULL;

ALTER TABLE contracts
    ADD COLUMN IF NOT EXISTS cancelled_by_id UUID NULL REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE contracts
    ADD COLUMN IF NOT EXISTS cancelled_reason TEXT NULL;
