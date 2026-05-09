-- Make user deletion cascade through the applicant tree (Django-admin style).
-- Was: ON DELETE RESTRICT — admin had to clear linked data manually.
-- Now: ON DELETE CASCADE — DELETE FROM users wipes the whole subtree.

-- =================================================================
-- Helper: drop-and-recreate FK with new ON DELETE rule.
-- (idempotent: silently skipped if the FK was already CASCADE.)
-- =================================================================
DO $$
DECLARE
    pair record;
BEGIN
    FOR pair IN
        SELECT * FROM (VALUES
            ('applicants',                  'fk_applicants_user_id_users',                       'user_id',           'users',        'id', 'CASCADE'),
            ('diploms',                     'fk_diploms_user_id_users',                          'user_id',           'users',        'id', 'CASCADE'),
            ('transfer_diploms',            'fk_transfer_diploms_user_id_users',                 'user_id',           'users',        'id', 'CASCADE'),
            ('applications',                'fk_applications_applicant_id_applicants',           'applicant_id',      'applicants',   'id', 'CASCADE'),
            ('contracts',                   'fk_contracts_application_id_applications',          'application_id',    'applications', 'id', 'CASCADE'),
            ('contract_parties',            'fk_contract_parties_contract_id_contracts',         'contract_id',       'contracts',    'id', 'CASCADE'),
            ('application_status_history',  'fk_application_status_history_application_id_applications', 'application_id', 'applications', 'id', 'CASCADE'),
            ('payments',                    'fk_payments_contract_id_contracts',                 'contract_id',       'contracts',    'id', 'CASCADE')
        ) AS t(child_table, fk_name, fk_column, parent_table, parent_column, action)
    LOOP
        -- Drop if it exists (under this name OR a different one).
        EXECUTE format(
            'ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I',
            pair.child_table, pair.fk_name
        );
        -- Recreate with CASCADE.
        EXECUTE format(
            'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %I (%I) ON DELETE %s',
            pair.child_table, pair.fk_name, pair.fk_column,
            pair.parent_table, pair.parent_column, pair.action
        );
    END LOOP;
END $$;

-- educations + diplom relationship (if present): ensure CASCADE up the chain.
-- Skip silently if the constraint name doesn't exist on this DB (legacy variants).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_educations_applicant_id_applicants') THEN
        ALTER TABLE educations DROP CONSTRAINT fk_educations_applicant_id_applicants;
        ALTER TABLE educations ADD CONSTRAINT fk_educations_applicant_id_applicants
            FOREIGN KEY (applicant_id) REFERENCES applicants(id) ON DELETE CASCADE;
    END IF;
END $$;
