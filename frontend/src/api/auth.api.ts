import { http } from '@/api/http'
import type { Role, User } from '@/types'

export interface OtpRequestResponse {
  phone: string
  expires_in: number
  resend_after: number
  delivered: boolean  // false = dev mode (no real SMS sent)
}

export interface AuthSession {
  user_id: string
  phone: string
  role: Role
  is_phone_verified: boolean
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginResponse {
  session: AuthSession
  tokens: TokenPair
}

export const authApi = {
  requestOtp: (phone: string) =>
    http.post<OtpRequestResponse>('/auth/otp/request', { phone }).then((r) => r.data),

  verifyOtp: (phone: string, code: string) =>
    http.post<LoginResponse>('/auth/otp/verify', { phone, code }).then((r) => r.data),

  staffLogin: (phone: string, password: string) =>
    http.post<LoginResponse>('/auth/login', { phone, password }).then((r) => r.data),

  refresh: (refresh_token: string) =>
    http.post<TokenPair>('/auth/refresh', { refresh_token }).then((r) => r.data),

  logout: (refresh_token: string) =>
    http.post('/auth/logout', { refresh_token }).then((r) => r.data),

  me: () => http.get<User>('/users/me').then((r) => r.data),
}

export function sessionToUser(session: AuthSession): User {
  return {
    id: session.user_id,
    phone: session.phone,
    role: session.role,
  }
}
