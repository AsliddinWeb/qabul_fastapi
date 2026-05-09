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
  /** Marker for users who can see the consulting_agency field on applications. */
  is_consulting?: boolean
  /** True only for the single root superadmin. Manages consulting agencies. */
  is_root_superadmin?: boolean
}

export interface ApiError {
  error: {
    code: string
    message: string
    details?: unknown
  }
}
