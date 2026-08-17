-- Editable marketing home-page content, managed from the admin panel.
-- Single-row JSON store; empty keys fall back to the landing's defaults.
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS landing_content (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
