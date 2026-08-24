/**
 * Frontend mirror of the backend's role → permissions matrix
 * (backend/app/core/permissions.py). Used only for UI gating; the backend
 * is still the source of truth and re-enforces every check on the wire.
 *
 * Keep this list in sync when adding new permissions. If a permission is
 * not listed here we treat it as "false" — better to hide a button than
 * to show one and 403 on click.
 */
import type { Role, User } from '@/types'

export type Permission =
  | 'contracts.read' | 'contracts.create' | 'contracts.sign'
  | 'payments.read' | 'payments.create' | 'payments.confirm' | 'payments.fail' | 'payments.refund'
  | 'applications.list' | 'applications.read' | 'applications.review' | 'applications.export'
  | 'applicants.list' | 'applicants.read' | 'applicants.write' | 'applicants.create_by_operator' | 'applicants.status'
  | 'leads.list' | 'leads.read' | 'leads.create' | 'leads.update' | 'leads.move'
  | 'leads.assign' | 'leads.convert' | 'leads.lose' | 'leads.delete' | 'leads.settings'
  | 'users.list' | 'users.read' | 'users.create' | 'users.update' | 'users.delete' | 'users.reset_password'
  | 'audit.read' | 'reports.view' | 'reports.financial'
  | 'contract_templates.read' | 'contract_templates.write'
  | 'intl_admissions.list' | 'intl_admissions.read'
  | 'intl_admissions.manage' | 'intl_admissions.delete'

const ROLE_PERMS: Record<Role, Permission[]> = {
  superadmin: [
    // Superadmin gets everything — listed explicitly so the type checker
    // catches typos rather than letting an unknown permission silently fail.
    'contracts.read', 'contracts.create', 'contracts.sign',
    'payments.read', 'payments.create', 'payments.confirm', 'payments.fail', 'payments.refund',
    'applications.list', 'applications.read', 'applications.review',
    'applicants.list', 'applicants.read', 'applicants.write', 'applicants.create_by_operator', 'applicants.status',
    'leads.list', 'leads.read', 'leads.create', 'leads.update', 'leads.move',
    'leads.assign', 'leads.convert', 'leads.lose', 'leads.delete', 'leads.settings',
    'users.list', 'users.read', 'users.create', 'users.update', 'users.delete', 'users.reset_password',
    'audit.read', 'reports.view', 'reports.financial',
    'contract_templates.read', 'contract_templates.write',
    'intl_admissions.list', 'intl_admissions.read', 'intl_admissions.manage', 'intl_admissions.delete',
  ],
  admin: [
    'contracts.read', 'contracts.create', 'contracts.sign',
    'payments.read',
    'applications.list', 'applications.read', 'applications.review',
    'applicants.list', 'applicants.read', 'applicants.write', 'applicants.create_by_operator', 'applicants.status',
    'leads.list', 'leads.read', 'leads.create', 'leads.update', 'leads.move',
    'leads.assign', 'leads.convert', 'leads.lose', 'leads.delete', 'leads.settings',
    'users.list', 'users.read', 'users.create', 'users.update', 'users.delete', 'users.reset_password',
    'audit.read', 'reports.view', 'reports.financial',
    'contract_templates.read', 'contract_templates.write',
    'intl_admissions.list', 'intl_admissions.read', 'intl_admissions.manage', 'intl_admissions.delete',
  ],
  operator: [
    'contracts.read', 'contracts.create', 'contracts.sign',
    'payments.read',
    'applications.list', 'applications.read', 'applications.review',
    'applicants.list', 'applicants.read', 'applicants.write', 'applicants.create_by_operator',
    'leads.list', 'leads.read', 'leads.create', 'leads.update', 'leads.move',
    'leads.assign', 'leads.convert', 'leads.lose',
    'contract_templates.read',
  ],
  director: [
    'contracts.read',
    'payments.read',
    'applications.list', 'applications.read',
    'applicants.list', 'applicants.read',
    'leads.list', 'leads.read',
    'users.list', 'users.read',
    'audit.read', 'reports.view', 'reports.financial',
    'contract_templates.read',
    'intl_admissions.list', 'intl_admissions.read',
  ],
  accountant: [
    'contracts.read', 'contracts.create', 'contracts.sign',
    'payments.read', 'payments.create', 'payments.confirm', 'payments.fail', 'payments.refund',
    'applications.list', 'applications.read', 'applications.export',
    'applicants.list', 'applicants.read',
    'reports.financial',
    'contract_templates.read',
  ],
  applicant: [
    'contracts.read', // own only — service-layer enforces ownership
  ],
}

/**
 * Effective permission check: role default ∧ not revoked for this user.
 *
 * `user.permissions_revoked` is propagated from `/users/me` and refreshed
 * by AppShell on mount. If the field is missing (older session), we fall
 * back to role defaults only — safe because the backend re-checks anyway.
 */
export function userHasPermission(user: User | null, perm: Permission): boolean {
  if (!user) return false
  const defaults = ROLE_PERMS[user.role] || []
  if (!defaults.includes(perm)) return false
  const revoked = Array.isArray(user.permissions_revoked) ? user.permissions_revoked : []
  return !revoked.includes(perm)
}

/** Permissions that are toggleable per user in the UserFormPage UI. */
export interface TogglablePerm {
  code: Permission
  label: string
  description: string
  roles: Role[]
}

export const TOGGLABLE_PERMISSIONS: TogglablePerm[] = [
  {
    code: 'contracts.create',
    label: 'Shartnoma yaratish',
    description: 'Ariza ostida yangi shartnoma yaratish huquqi.',
    roles: ['superadmin', 'admin', 'operator', 'accountant'],
  },
  {
    code: 'contracts.sign',
    label: 'Shartnomalarni imzolash',
    description: 'Yaratilgan shartnomani "imzolangan" deb belgilash huquqi.',
    roles: ['superadmin', 'admin', 'operator', 'accountant'],
  },
  {
    code: 'leads.convert',
    label: "Lead'ni arizaga o'tkazish",
    description: "Lead'dan ariza yaratish (konversiya).",
    roles: ['superadmin', 'admin', 'operator'],
  },
  {
    code: 'leads.delete',
    label: "Lead'larni o'chirish",
    description: "Lead'larni butunlay o'chirib tashlash.",
    roles: ['superadmin', 'admin'],
  },
  {
    code: 'applications.export',
    label: "Arizalarni yuklab olish",
    description: "Arizalarni Excel/CSV sifatida eksport qilish (audit'ga yoziladi).",
    roles: ['accountant'],
  },
  {
    code: 'payments.confirm',
    label: "To'lovlarni tasdiqlash",
    description: "Kutilayotgan to'lovlarni tasdiqlash.",
    roles: ['superadmin', 'admin', 'accountant'],
  },
  {
    code: 'payments.refund',
    label: "To'lovlarni qaytarish",
    description: "Tasdiqlangan to'lovni refund qilish.",
    roles: ['superadmin', 'admin', 'accountant'],
  },
  {
    code: 'applications.review',
    label: "Arizani ko'rib chiqish",
    description: "Arizani qabul/rad etish huquqi.",
    roles: ['superadmin', 'admin', 'operator'],
  },
]
