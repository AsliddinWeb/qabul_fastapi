import { defineStore } from 'pinia'
import { http } from '@/api/http'

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

export const useSidebarCounts = defineStore('sidebarCounts', {
  state: (): { counts: CountState; loading: boolean } => ({
    counts: { ...EMPTY },
    loading: false,
  }),
  actions: {
    async refresh() {
      this.loading = true
      try {
        const [leads, applicants, applications, contracts, payments, users, audit, referrals] = await Promise.all([
          totalFor('/leads'),
          totalFor('/applicants'),
          totalFor('/applications'),
          totalFor('/contracts'),
          totalFor('/payments'),
          totalFor('/users'),
          totalFor('/audit'),
          totalFor('/referrals'),
        ])
        this.counts = {
          leads, applicants, applications, contracts,
          payments, users, audit, referrals,
        }
      } finally {
        this.loading = false
      }
    },
    reset() {
      this.counts = { ...EMPTY }
    },
  },
})
