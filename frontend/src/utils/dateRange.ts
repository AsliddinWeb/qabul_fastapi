/**
 * Helpers for the DateRangeFilter component.
 *
 * The component holds the value as a plain "YYYY-MM-DD" local date so the
 * URL filter layer can round-trip it cleanly. When we actually call the
 * API we need to convert each end to a UTC ISO timestamp matching the
 * inclusive semantics the user expects:
 *
 *   from "2026-06-10" → "2026-06-10T00:00:00.000Z" (local midnight of that day)
 *   to   "2026-06-10" → "2026-06-10T23:59:59.999Z" (local end of that day)
 *
 * The trick: new Date("2026-06-10") parses as UTC midnight, but the user
 * thinks of June 10 in their own timezone. We construct the date with
 * Y/M/D constructor args (which use LOCAL time) then call toISOString()
 * to get the UTC equivalent — exactly what the backend wants for its
 * `created_at >= from / <= to` comparison.
 *
 * Returns undefined for empty strings so axios drops the query param
 * entirely instead of sending `?created_from=`.
 */

function parseYmd(ymd: string): [number, number, number] | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd)
  if (!m) return null
  return [Number(m[1]), Number(m[2]) - 1, Number(m[3])]
}

/** "2026-06-10" → "2026-06-10T00:00:00.000Z" (local midnight as UTC ISO). */
export function toApiFrom(ymd: string): string | undefined {
  const parsed = parseYmd(ymd)
  if (!parsed) return undefined
  const [y, m, d] = parsed
  return new Date(y, m, d, 0, 0, 0, 0).toISOString()
}

/** "2026-06-10" → "2026-06-10T23:59:59.999Z" (local end-of-day as UTC ISO). */
export function toApiTo(ymd: string): string | undefined {
  const parsed = parseYmd(ymd)
  if (!parsed) return undefined
  const [y, m, d] = parsed
  return new Date(y, m, d, 23, 59, 59, 999).toISOString()
}
