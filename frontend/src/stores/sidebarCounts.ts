import { defineStore } from 'pinia'
import { http } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { usePanelsStore, type NavEntry } from '@/stores/panels'

/**
 * Sidebar-counts store: holds total-row counts for the operational pages
 * (leads, applicants, applications, etc.) so SidebarNav can render
 * "Lead'lar ro'yxati (1700)"-style badges next to nav entries.
 *
 * Each count is fetched with `page=1, size=1` against the corresponding
 * list endpoint — we only need the `total` field. Failures are silent
 * (null) so a permission-denied call doesn't break the whole sidebar.
 *
 * AppShell triggers refresh() on mount + every 60 seconds while the panel
 * is open. Individual pages can call refresh() after a mutation that
 * changes a count (e.g. deleting an application) if they care about it
 * being immediately fresh, but the periodic poll is usually enough.
 */
export type CountKey =
  | 'leads'
  | 'applicants'
  | 'applications'
  | 'contracts'
  | 'payments'
  | 'users'
  | 'audit'
  | 'referrals'

type CountState = Record<CountKey, number | null>

const EMPTY: CountState = {
  leads: null,
  applicants: null,
  applications: null,
  contracts: null,
  payments: null,
  users: null,
  audit: null,
  referrals: null,
}

async function totalFor(path: string, params: Record<string, any> = {}): Promise<number | null> {
  try {
    const res = await http.get<{ total: number }>(path, { params: { page: 1, size: 1, ...params } })
    return typeof res.data?.total === 'number' ? res.data.total : null
  } catch {
    return null
  }
}

// Map countKey → list endpoint. Adding a new countKey only needs an entry
// here plus the corresponding label in panels.ts/NavLeaf.countKey.
const ENDPOINT_FOR: Record<CountKey, string> = {
  leads: '/leads',
  applicants: '/applicants',
  applications: '/applications',
  contracts: '/contracts',
  payments: '/payments',
  users: '/users',
  audit: '/audit',
  referrals: '/referrals',
}

function collectKeys(nav: NavEntry[]): Set<CountKey> {
  const out = new Set<CountKey>()
  for (const e of nav) {
    if (e.type === 'leaf' && e.countKey) out.add(e.countKey)
    else if (e.type === 'group') for (const c of e.items) if (c.countKey) out.add(c.countKey)
  }
  return out
}

export const useSidebarCounts = defineStore('sidebarCounts', {
  state: (): { counts: CountState; loading: boolean } => ({
    counts: { ...EMPTY },
    loading: false,
  }),
  actions: {
    async refresh() {
      // Only fetch counts for keys the current panel actually shows. Saves
      // a guaranteed-403 round-trip (e.g. operator hitting /users) and
      // keeps the browser console clean of permission errors.
      const panels = usePanelsStore()
      const panel = panels.currentPanel
      if (!panel) return
      const keys = collectKeys(panel.nav)
      if (!keys.size) return

      // On the operator panel the list pages auto-scope to the current
      // operator. The sidebar badge needs the SAME scope or it'll show
      // colleagues' counts and confuse the operator. Map each key to its
      // operator-scope filter param so the totals line up with what the
      // page actually renders.
      const isOperator = panels.currentPanel?.key === 'operator'
      const userId = useAuthStore().user?.id
      const scoped = isOperator && userId
      function paramsFor(k: CountKey): Record<string, any> {
        if (!scoped) return {}
        switch (k) {
          case 'leads':         return { assigned_to_id: userId }
          case 'applicants':    return { registered_by_id: userId }
          case 'applications':  return { registered_by_id: userId }
          case 'contracts':     return { created_by_id: userId }
          case 'payments':      return { registered_by_id: userId }
          default:              return {}
        }
      }

      this.loading = true
      try {
        const fresh: CountState = { ...EMPTY }
        await Promise.all(
          Array.from(keys).map(async (k) => {
            fresh[k] = await totalFor(ENDPOINT_FOR[k], paramsFor(k))
          }),
        )
        // Preserve any count from a previous panel (rare; user role change)
        // but newly-fetched keys overwrite.
        this.counts = { ...this.counts, ...fresh }
      } finally {
        this.loading = false
      }
    },
    reset() {
      this.counts = { ...EMPTY }
    },
  },
})
