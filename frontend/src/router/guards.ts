import type { NavigationGuard } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types'

/** Default landing route per role. */
export function homePathForRole(role: Role | null | undefined): string {
  switch (role) {
    case 'superadmin':
    case 'admin':      return '/admin'
    case 'operator':   return '/operator'
    case 'director':   return '/director'
    case 'accountant': return '/accountant'
    case 'applicant':  return '/applicant'
    default:           return '/auth/login'
  }
}

/** Smart "/" redirect: authenticated users → role home, otherwise login. */
export const rootRedirect: NavigationGuard = (_to, _from, next) => {
  const auth = useAuthStore()
  if (auth.isAuthenticated && auth.role) {
    return next(homePathForRole(auth.role))
  }
  next({ name: 'phone-login' })
}

/** Block already-authenticated users from /auth/* pages. */
export const redirectIfAuthenticated: NavigationGuard = (_to, _from, next) => {
  const auth = useAuthStore()
  if (auth.isAuthenticated && auth.role) {
    return next(homePathForRole(auth.role))
  }
  next()
}

export const requireAuth: NavigationGuard = (to, _from, next) => {
  const auth = useAuthStore()
  if (!auth.isAuthenticated) {
    return next({ name: 'phone-login', query: { redirect: to.fullPath } })
  }
  next()
}

export const requireRoles =
  (roles: Role[]): NavigationGuard =>
  (to, _from, next) => {
    const auth = useAuthStore()
    if (!auth.isAuthenticated) {
      return next({ name: 'phone-login', query: { redirect: to.fullPath } })
    }
    if (!auth.role || !roles.includes(auth.role)) {
      return next({ name: 'forbidden' })
    }
    next()
  }
