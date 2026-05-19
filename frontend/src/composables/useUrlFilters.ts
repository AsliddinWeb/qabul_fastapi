/**
 * URL-backed filter state.
 *
 * Why: every list page (leads, applications, audit, …) used local reactive
 * state. Clicking a row → drilling into a detail → browser back wiped the
 * filters because the URL had no record of them. Pushing filters into
 * `route.query` makes "back" restore them automatically, gives every
 * filtered view a shareable URL, and lets us add a "Tozalash" button by
 * just resetting the query.
 *
 * Usage:
 *   const { filters, clear, hasActiveFilters } = useUrlFilters({
 *     search: '',
 *     status: '',
 *     page: 1,
 *   })
 *
 * The composable:
 *   • Hydrates `filters` from `route.query` on mount (typed coerce for
 *     numbers/booleans based on the default value's type).
 *   • Watches `filters` deeply and calls `router.replace(...)` — replace,
 *     not push, so we don't pollute history with every keystroke.
 *   • Omits any value equal to the default from the URL — keeps URLs
 *     short and "no filters" reads as `?` or `/path`.
 *   • Watches `route.query` (e.g. browser back/forward) and rehydrates.
 */
import { reactive, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQuery } from 'vue-router'

type Primitive = string | number | boolean | null | undefined
type FilterShape = Record<string, Primitive>

function coerce<T extends Primitive>(raw: unknown, sample: T): T {
  if (raw === undefined || raw === null) return sample
  if (Array.isArray(raw)) raw = raw[0]
  const s = String(raw)
  if (typeof sample === 'number') {
    const n = Number(s)
    return (Number.isFinite(n) ? n : sample) as T
  }
  if (typeof sample === 'boolean') return (s === 'true' || s === '1') as T
  return s as T
}

function readFromQuery<T extends FilterShape>(query: LocationQuery, defaults: T): T {
  const out: any = { ...defaults }
  for (const key of Object.keys(defaults) as Array<keyof T>) {
    if (key in query) {
      out[key] = coerce(query[key as string], defaults[key])
    }
  }
  return out
}

function isDefaultValue(v: Primitive, def: Primitive): boolean {
  if (v === def) return true
  if (v === '' && (def === '' || def === null || def === undefined)) return true
  if (v === null && (def === '' || def === null)) return true
  return false
}

function serializeToQuery<T extends FilterShape>(filters: T, defaults: T): Record<string, string> {
  const out: Record<string, string> = {}
  for (const key of Object.keys(filters)) {
    const v = filters[key]
    if (isDefaultValue(v as Primitive, defaults[key])) continue
    if (v === null || v === undefined) continue
    out[key] = String(v)
  }
  return out
}

export function useUrlFilters<T extends FilterShape>(defaults: T) {
  const route = useRoute()
  const router = useRouter()

  // Initial state — overlay current URL on top of defaults.
  const filters = reactive(readFromQuery(route.query, defaults)) as T

  // Avoid loop: skip URL writes triggered by our own URL→state hydration.
  let pendingHydration = false

  watch(
    () => ({ ...filters }),
    (next) => {
      if (pendingHydration) { pendingHydration = false; return }
      const q = serializeToQuery(next as T, defaults)
      router.replace({ path: route.path, query: q })
    },
    { deep: true },
  )

  // External URL change (back/forward, manual edit, paste) → rehydrate.
  watch(
    () => route.query,
    (q) => {
      const next = readFromQuery(q, defaults)
      // Skip if nothing changed (replace-with-same-state ping-pong).
      let same = true
      for (const k of Object.keys(defaults)) {
        if ((next as any)[k] !== (filters as any)[k]) { same = false; break }
      }
      if (same) return
      pendingHydration = true
      Object.assign(filters, next)
    },
  )

  function clear() {
    pendingHydration = true
    Object.assign(filters, defaults)
    router.replace({ path: route.path, query: {} })
  }

  const hasActiveFilters = computed(() => {
    for (const k of Object.keys(defaults)) {
      if (!isDefaultValue((filters as any)[k], defaults[k])) return true
    }
    return false
  })

  return { filters, clear, hasActiveFilters }
}
