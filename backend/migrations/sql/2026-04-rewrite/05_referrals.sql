-- Referral programme: invitee gives the inviter a 500,000 som bonus once the
-- referred student has paid 25%+ of their contract. The bonus can be redeemed
-- either as a discount on the inviter's own contract or as a cash payout.
--
-- Schema:
--   users.referral_code  — public, unique 6-char code each user can share
--   referrals            — one row per (inviter, invitee) pair
--   referral_settings    — singleton (reward_amount, qualification %)
--   referral_payouts     — cash withdrawal queue (added here so phase-4 only
--                          needs UI work, no further migrations)
--
-- Idempotent: ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS, no
-- destructive operations.

-- ---------- 1. users.referral_code ----------
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS referral_code VARCHAR(8);

-- Backfill: every existing user gets a code derived from a portion of their
-- id (8 hex chars, uppercased). This guarantees uniqueness without a separate
-- random loop. New users will get a code on insert via the application.
UPDATE users
SET referral_code = UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 6))
WHERE referral_code IS NULL;

-- Enforce uniqueness now that the column is populated.
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_referral_code_unique
    ON users (referral_code)
    WHERE referral_code IS NOT NULL;


-- ---------- 2. referral_settings (singleton) ----------
CREATE TABLE IF NOT EXISTS referral_settings (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reward_amount            NUMERIC(14, 2) NOT NULL DEFAULT 500000,
    qualification_percent    NUMERIC(5, 2)  NOT NULL DEFAULT 25,
    is_active                BOOLEAN        NOT NULL DEFAULT true,
    created_at               TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- Seed the singleton row if missing.
INSERT INTO referral_settings (reward_amount, qualification_percent, is_active)
SELECT 500000, 25, true
WHERE NOT EXISTS (SELECT 1 FROM referral_settings);


-- ---------- 3. referrals ----------
CREATE TABLE IF NOT EXISTS referrals (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who invited (must be an existing user with a referral_code)
    referrer_user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- The applicant that was invited
    referred_applicant_id    UUID NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    -- The contract that drives qualification (filled when contract created)
    contract_id              UUID NULL REFERENCES contracts(id) ON DELETE SET NULL,

    -- pending → active → spent_on_contract / paid_cash / cancelled
    status                   VARCHAR(40) NOT NULL DEFAULT 'pending',
    reward_amount            NUMERIC(14, 2) NOT NULL DEFAULT 500000,

    -- Where the referrer met / signed up the referee. "link" = via ?ref=
    -- code; "manual" = operator/applicant typed it in.
    source                   VARCHAR(20) NOT NULL DEFAULT 'manual',

    -- Lifecycle timestamps
    activated_at             TIMESTAMPTZ NULL,
    cancelled_at             TIMESTAMPTZ NULL,
    payout_at                TIMESTAMPTZ NULL,

    -- Redemption pointers
    applied_contract_id      UUID NULL REFERENCES contracts(id) ON DELETE SET NULL,
    cash_payout_id           UUID NULL,  -- referral_payouts.id (loose FK below)

    cancelled_reason         TEXT NULL,
    notes                    TEXT NULL,

    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Each applicant can only be referred once.
    CONSTRAINT uq_referrals_referred_applicant UNIQUE (referred_applicant_id)
);

CREATE INDEX IF NOT EXISTS ix_referrals_referrer ON referrals (referrer_user_id);
CREATE INDEX IF NOT EXISTS ix_referrals_status   ON referrals (status);
CREATE INDEX IF NOT EXISTS ix_referrals_contract ON referrals (contract_id);


-- ---------- 4. referral_payouts (cash withdrawal queue) ----------
CREATE TABLE IF NOT EXISTS referral_payouts (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    referrer_user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount                   NUMERIC(14, 2) NOT NULL,
    referral_count           INTEGER NOT NULL,

    -- requested → approved → paid / rejected
    status                   VARCHAR(20) NOT NULL DEFAULT 'requested',

    requested_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_by_user_id      UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    approved_at              TIMESTAMPTZ NULL,
    paid_at                  TIMESTAMPTZ NULL,
    rejected_reason          TEXT NULL,
    notes                    TEXT NULL,

    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_referral_payouts_referrer ON referral_payouts (referrer_user_id);
CREATE INDEX IF NOT EXISTS ix_referral_payouts_status   ON referral_payouts (status);

-- Now that referral_payouts exists, attach the FK from referrals.cash_payout_id.
-- We add it AFTER the table so the two CREATE blocks can run in any order on
-- a fresh DB; ADD CONSTRAINT IF NOT EXISTS isn't supported, so guard with DO.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_referrals_cash_payout'
    ) THEN
        ALTER TABLE referrals
            ADD CONSTRAINT fk_referrals_cash_payout
            FOREIGN KEY (cash_payout_id) REFERENCES referral_payouts(id)
            ON DELETE SET NULL;
    END IF;
END $$;
