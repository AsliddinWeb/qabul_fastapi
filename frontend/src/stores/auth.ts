import { defineStore } from 'pinia'
import type { Role, User } from '@/types'

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

  getters: {
    isAuthenticated: (s) => !!s.accessToken,
    role: (s): Role | null => s.user?.role ?? null,
    /** True only for the single root user — they manage consulting agencies. */
    isRootSuperadmin: (s) => !!s.user?.is_root_superadmin,
    /** True for users marked is_consulting (root included), used to gate
     *  the consulting_agency field/filter on application screens. */
    isConsulting: (s) => !!(s.user?.is_consulting || s.user?.is_root_superadmin),
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
