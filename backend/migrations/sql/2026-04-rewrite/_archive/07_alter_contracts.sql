-- 07: Contract templates — add 2-party / 3-party RichText body fields.
-- Add contract_settings singleton table.
BEGIN;

-- ---- Templates: add Django-style fields, make legacy fields nullable
ALTER TABLE contract_templates
    ADD COLUMN IF NOT EXISTS body_two_party TEXT,
    ADD COLUMN IF NOT EXISTS body_three_party TEXT;

-- Make old required fields optional (since new templates won't fill them)
ALTER TABLE contract_templates ALTER COLUMN type DROP NOT NULL;
ALTER TABLE contract_templates ALTER COLUMN language DROP NOT NULL;
ALTER TABLE contract_templates ALTER COLUMN body_html DROP NOT NULL;

-- Drop FK to dictionary_items.education_level_id (we don't use this anymore on templates)
ALTER TABLE contract_templates DROP CONSTRAINT IF EXISTS fk_contract_templates_education_level_id_dictionary_items;
ALTER TABLE contract_templates DROP COLUMN IF EXISTS education_level_id;

-- Default templates inactive (single-active rule enforced at app layer)
ALTER TABLE contract_templates ALTER COLUMN is_active SET DEFAULT FALSE;

-- ---- Settings singleton
CREATE TABLE IF NOT EXISTS contract_settings (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    default_contract_type    contract_type NOT NULL DEFAULT 'two_party',
    auto_generate_pdf        BOOLEAN NOT NULL DEFAULT TRUE,
    pdf_page_size            VARCHAR(10) NOT NULL DEFAULT 'A4',
    company_name             VARCHAR(200) NOT NULL DEFAULT 'Ta''lim muassasasi',
    company_address          TEXT,
    director_name            VARCHAR(100),
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
