-- Leads kanban board pagination support.
--
-- The board now loads a small page of cards per stage
-- (WHERE stage_id = ? AND status IN ('open','won') ORDER BY created_at DESC
-- LIMIT 30). This composite index lets Postgres return each page as an
-- ordered index scan instead of sorting the whole stage — the difference
-- between instant and multi-second at 10k+ leads.
--
-- Idempotent: safe to re-run.

CREATE INDEX IF NOT EXISTS ix_leads_stage_created
    ON public.leads USING btree (stage_id, created_at DESC);
