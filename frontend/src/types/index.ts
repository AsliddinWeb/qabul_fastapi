export type Role =
  | 'superadmin'
  | 'admin'
  | 'operator'
  | 'director'
  | 'accountant'
  | 'applicant'

export interface User {
  id: string
  phone: string
  full_name?: string
  role: Role
}

export interface ApiError {
  error: {
    code: string
    message: string
    details?: unknown
  }
}
