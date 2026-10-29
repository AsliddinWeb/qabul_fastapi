-- Kontrakt to'loviga chegirma vaucherlari (faqat o'qishni ko'chirish arizalari).
-- PDF is rendered on demand from the snapshot columns below — no file stored.
-- Idempotent: safe to re-run.

CREATE SEQUENCE IF NOT EXISTS voucher_number_seq START 1;

CREATE TABLE IF NOT EXISTS vouchers (
    id                UUID PRIMARY KEY,
    voucher_number    INTEGER NOT NULL UNIQUE DEFAULT nextval('voucher_number_seq'),
    application_id    UUID NOT NULL REFERENCES applications(id) ON DELETE RESTRICT,
    contract_id       UUID REFERENCES contracts(id) ON DELETE SET NULL,
    discount_percent  SMALLINT NOT NULL DEFAULT 50,
    student_full_name VARCHAR(255) NOT NULL,
    program_name      VARCHAR(255) NOT NULL,
    valid_until       DATE NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'active',
    created_by_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    cancelled_at      TIMESTAMPTZ,
    cancelled_by_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    cancelled_reason  TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER SEQUENCE voucher_number_seq OWNED BY vouchers.voucher_number;

CREATE INDEX IF NOT EXISTS ix_vouchers_application_id ON vouchers (application_id);
CREATE INDEX IF NOT EXISTS ix_vouchers_contract_id    ON vouchers (contract_id);
CREATE INDEX IF NOT EXISTS ix_vouchers_status         ON vouchers (status);

-- At most one ACTIVE voucher per application.
CREATE UNIQUE INDEX IF NOT EXISTS uq_vouchers_application_active
    ON vouchers (application_id) WHERE status = 'active';
