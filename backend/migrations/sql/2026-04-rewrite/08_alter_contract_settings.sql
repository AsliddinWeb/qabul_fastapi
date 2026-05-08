-- ContractSettings: add company_inn and director_title columns.
-- These were previously held in env (UNIVERSITY_INN, UNIVERSITY_DIRECTOR_TITLE)
-- but were moved to admin-managed runtime settings.

ALTER TABLE contract_settings
    ADD COLUMN IF NOT EXISTS company_inn VARCHAR(20),
    ADD COLUMN IF NOT EXISTS director_title VARCHAR(50) NOT NULL DEFAULT 'Rektor';

-- Update default for company_name from generic to actual.
ALTER TABLE contract_settings ALTER COLUMN company_name SET DEFAULT 'Xalqaro Innovatsion Universiteti';
UPDATE contract_settings SET company_name = 'Xalqaro Innovatsion Universiteti'
    WHERE company_name = 'Ta''lim muassasasi';
