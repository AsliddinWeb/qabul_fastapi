#!/usr/bin/env bash
# Apply all 2026-04-rewrite SQL migrations in order, inside the postgres container.
# Usage: ./runner.sh
#
# Idempotent: each script uses CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS / etc.
set -euo pipefail

MIG_DIR="/migrations/2026-04-rewrite"

for sql in "$MIG_DIR"/*.sql; do
    echo "==> applying $(basename "$sql")"
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$sql"
done

echo "All migrations applied."
