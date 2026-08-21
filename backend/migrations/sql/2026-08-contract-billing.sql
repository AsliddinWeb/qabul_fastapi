-- "Billing" contracts: an external, state-issued PDF uploaded in place of a
-- system-generated contract. It occupies the same single-active-contract slot
-- per application (existing partial unique index), so the system can't issue a
-- contract while a billing one is active, and vice-versa.
-- Idempotent: safe to re-run.

-- source: 'system' (template-generated, default) | 'external' (uploaded billing PDF)
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'system';

-- A billing contract has no template — its PDF is uploaded, not rendered.
ALTER TABLE contracts ALTER COLUMN template_id DROP NOT NULL;
