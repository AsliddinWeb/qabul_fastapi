-- Consulting agencies (sayt orqali ariza kim orqali kelganini kuzatish uchun)
-- + ikki yangi user flag:
--   * is_root_superadmin — faqat shu user agencies'ni boshqaradi (faqat 1 ta).
--   * is_consulting — bu marker qo'yilgan foydalanuvchilar arizada
--     consulting_agency maydonini va filterni ko'rishi mumkin.

CREATE TABLE IF NOT EXISTS consulting_agencies (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(150) NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_consulting_agencies_name UNIQUE (name)
);

CREATE INDEX IF NOT EXISTS ix_consulting_agencies_is_active
    ON consulting_agencies (is_active);

-- Applications FK
ALTER TABLE applications
    ADD COLUMN IF NOT EXISTS consulting_agency_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_applications_consulting_agency_id'
    ) THEN
        ALTER TABLE applications
            ADD CONSTRAINT fk_applications_consulting_agency_id
            FOREIGN KEY (consulting_agency_id)
            REFERENCES consulting_agencies(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_applications_consulting_agency_id
    ON applications (consulting_agency_id);

-- User flags
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_consulting BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS is_root_superadmin BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_users_is_consulting ON users (is_consulting);

-- Promote the first-ever superadmin to root (single source of truth) if no
-- root has been set yet. Run-once idempotent.
UPDATE users SET is_root_superadmin = TRUE
WHERE id = (
    SELECT id FROM users
    WHERE role = 'superadmin' AND deleted_at IS NULL
    ORDER BY created_at ASC LIMIT 1
)
AND NOT EXISTS (SELECT 1 FROM users WHERE is_root_superadmin = TRUE);
