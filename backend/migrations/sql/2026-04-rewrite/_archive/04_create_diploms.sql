-- 04: Diploms catalog (education_types, institution_types, courses)
-- and Diplom + TransferDiplom (under applicants module domain)
BEGIN;

CREATE TABLE IF NOT EXISTS education_types (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS institution_types (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS courses (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed
INSERT INTO education_types (name)
VALUES ('Bakalavr'), ('Magistratura'), ('O''rta-maxsus'), ('Akademik litsey')
ON CONFLICT (name) DO NOTHING;

INSERT INTO institution_types (name)
VALUES ('Universitet'), ('Institut'), ('Akademiya'), ('Kollej'), ('Litsey')
ON CONFLICT (name) DO NOTHING;

INSERT INTO courses (name)
VALUES ('1-kurs'), ('2-kurs'), ('3-kurs'), ('4-kurs'), ('5-kurs')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS diploms (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    serial_number         VARCHAR(100) NOT NULL,
    education_type_id     UUID NOT NULL REFERENCES education_types(id) ON DELETE RESTRICT,
    institution_type_id   UUID NOT NULL REFERENCES institution_types(id) ON DELETE RESTRICT,
    university_name       TEXT NOT NULL,
    graduation_year       VARCHAR(4) NOT NULL,
    region_id             UUID NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    district_id           UUID NOT NULL REFERENCES districts(id) ON DELETE RESTRICT,
    diploma_file_id       UUID REFERENCES files(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_diploms_user_id UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS transfer_diploms (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    country_id            UUID NOT NULL REFERENCES countries(id) ON DELETE RESTRICT,
    university_name       TEXT NOT NULL,
    target_course_id      UUID NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    transcript_file_id    UUID REFERENCES files(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_transfer_diploms_user_id UNIQUE (user_id)
);

COMMIT;
