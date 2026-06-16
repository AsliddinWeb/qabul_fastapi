/**
 * Auth-only "directory" lookup for users.
 *
 * The full /users CRUD lives under adminApi.users and requires
 * users.list / users.read / users.update permissions. Operators
 * don't have any of those, but they STILL need to see basic team
 * info on detail pages — "who registered this applicant", "who
 * created the contract", "list of teammates to reassign a lead
 * to". This thin wrapper around /users/public-lookup gives every
 * authenticated user access to:
 *
 *   { id, full_name, phone, role, referral_code }
 *
 * — and nothing else. No is_active, no last_login_at, no audit
 * timestamps. Two query shapes:
 *
 *   byIds([u1, u2, …])         → bulk resolve actor names
 *   byRole('operator')         → populate the "Operator" filter
 *                                dropdown on list pages
 *
 * Use adminApi.users.get / adminApi.users.list when the caller
 * holds users.read / users.list (admin pages, settings). Use this
 * helper for shared widgets that render across all staff roles.
 */
import { http } from '@/api/http'

export interface UserLookup {
  id: string
  full_name: string | null
  phone: string | null
  role: string | null
  referral_code: string | null
}

export const usersApi = {
  /** Bulk resolve actor names by id. Skips invalid ids server-side. */
  byIds: (ids: string[]) => {
    if (!ids.length) return Promise.resolve([] as UserLookup[])
    return http.get<UserLookup[]>('/users/public-lookup', {
      params: { ids: ids.join(',') },
    }).then(r => r.data)
  },

  /** All users of a role (operator / accountant / …). Capped at 200. */
  byRole: (role: string, limit = 200) =>
    http.get<UserLookup[]>('/users/public-lookup', {
      params: { role, limit },
    }).then(r => r.data),

  /** Single id — convenience wrapper around byIds for components that
   *  just want one user (LoginInfoCard, etc.). Returns null on miss. */
  one: async (id: string): Promise<UserLookup | null> => {
    const rows = await usersApi.byIds([id])
    return rows[0] || null
  },
}
