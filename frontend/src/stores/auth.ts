import { defineStore } from 'pinia'
import type { Role, User } from '@/types'
import { userHasPermission, type Permission } from '@/utils/permissions'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),

  hydrate(state) {
    // Pinia calls hydrate after state init; we use it to subscribe to the
    // browser's `storage` event so a token refresh in tab A propagates into
    // tab B (otherwise tab B keeps using the rotated-out refresh token and
    // the server eventually flags reuse and revokes every session).
    if (typeof window !== 'undefined' && !(window as any).__authStorageBound) {
      ;(window as any).__authStorageBound = true
      window.addEventListener('storage', (e) => {
        if (e.key === 'access_token') state.accessToken = e.newValue
        if (e.key === 'refresh_token') state.refreshToken = e.newValue
        if (e.key === 'user') {
          try { state.user = e.newValue ? JSON.parse(e.newValue) : null } catch { /* ignore */ }
        }
      })
    }
  },

  getters: {
    isAuthenticated: (s) => !!s.accessToken,
    role: (s): Role | null => s.user?.role ?? null,
    /** True only for the single root user — they manage consulting agencies. */
    isRootSuperadmin: (s) => !!s.user?.is_root_superadmin,
    /** True for users marked is_consulting (root included), used to gate
     *  the consulting_agency field/filter on application screens. */
    isConsulting: (s) => !!(s.user?.is_consulting || s.user?.is_root_superadmin),
    /** Effective permission check: role default ∧ not revoked for this user.
     *  Mirrors the backend matrix; backend re-checks every request. */
    hasPermission: (s) => (perm: Permission) => userHasPermission(s.user, perm),
  },

  actions: {
    setSession(access: string, refresh: string, user: User) {
      this.accessToken = access
      this.refreshToken = refresh
      this.user = user
      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)
      localStorage.setItem('user', JSON.stringify(user))
    },
    logout() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    },
  },
})
