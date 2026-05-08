-- 01: countries / regions / districts (3-tier geography)
BEGIN;

CREATE TABLE IF NOT EXISTS countries (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS regions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    country_id  UUID NOT NULL REFERENCES countries(id) ON DELETE RESTRICT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_regions_name_country UNIQUE (name, country_id)
);
CREATE INDEX IF NOT EXISTS ix_regions_country_id ON regions(country_id);

CREATE TABLE IF NOT EXISTS districts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    region_id   UUID NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_districts_name_region UNIQUE (name, region_id)
);
CREATE INDEX IF NOT EXISTS ix_districts_region_id ON districts(region_id);

COMMIT;
