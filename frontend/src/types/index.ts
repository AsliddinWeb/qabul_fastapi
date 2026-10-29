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
  /** Permission codes the admin has switched off for this specific user. Used
   *  alongside the role default list to compute effective permissions. */
  permissions_revoked?: string[]
  /** Opt-in extras granted on top of the role (e.g. applications.view_all). */
  permissions_granted?: string[]
}

export interface ApiError {
  error: {
    code: string
    message: string
    details?: unknown
  }
}
