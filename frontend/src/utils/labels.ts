/**
 * Uzbek display labels for backend enums.
 * Used everywhere the user-facing app shows a status/role/etc.
 */

export const APPLICATION_STATUS: Record<string, string> = {
  topshirildi:        'Topshirildi',
  korib_chiqilmoqda:  "Ko'rib chiqilmoqda",
  qabul_qilindi:      'Qabul qilindi',
  rad_etildi:         'Rad etildi',
}

export const ADMISSION_TYPE: Record<string, string> = {
  yangi_qabul: '1-kurs (Yangi qabul)',
  perevod:     'Perevod',
}

export const CONTRACT_STATUS: Record<string, string> = {
  draft:     'Qoralama',
  signed:    'Imzolangan',
  cancelled: 'Bekor qilingan',
  completed: 'Yakunlangan',
}

export const PAYMENT_STATUS: Record<string, string> = {
  pending:   'Kutilmoqda',
  confirmed: 'Tasdiqlangan',
  failed:    'Bajarilmadi',
  refunded:  'Qaytarilgan',
}

export const ROLE: Record<string, string> = {
  superadmin: 'Bosh administrator',
  admin:      'Administrator',
  operator:   'Operator',
  director:   'Direktor',
  accountant: 'Buxgalter',
  applicant:  'Abituriyent',
}

export const CONTRACT_TYPE: Record<string, string> = {
  two_party:   '2-tomonlama',
  three_party: '3-tomonlama',
}

export function tr(map: Record<string, string>, key: string | null | undefined): string {
  if (!key) return '—'
  return map[key] || key
}

// ===== Audit log labels =====

export const AUDIT_ACTIONS: Record<string, string> = {
  // User
  'user.create':           'Foydalanuvchi yaratildi',
  'user.update':           'Foydalanuvchi tahrirlandi',
  'user.delete':           "Foydalanuvchi o'chirildi",
  'user.reset_password':   "Foydalanuvchining paroli tiklandi",
  // Applicant
  'applicant.create_by_operator': 'Abituriyent qo\'shildi (operator)',
  'applicant.create':      "Abituriyent yaratildi",
  'applicant.update':      "Abituriyent tahrirlandi",
  // Application
  'application.create':            'Ariza topshirildi',
  'application.create_by_staff':   "Ariza yaratildi (xodim)",
  'application.review':            "Ariza ko'rib chiqildi",
  'application.start_review':      "Ariza ko'rib chiqishga olindi",
  'application.withdraw':          "Ariza qaytarib olindi",
  'application.update':            "Ariza tahrirlandi",
  'application.delete':            "Ariza o'chirildi",
  // Contract
  'contract.create':       "Shartnoma yaratildi",
  'contract.sign':         "Shartnoma imzolandi",
  'contract.cancel':       "Shartnoma bekor qilindi",
  // Payment
  'payment.create':        "To'lov qo'shildi",
  'payment.confirm':       "To'lov tasdiqlandi",
  'payment.refund':        "To'lov qaytarildi",
  'payment.fail':          "To'lov bajarilmadi",
  // Lead (CRM)
  'lead.create':           'Lead yaratildi',
  'lead.update':           'Lead tahrirlandi',
  'lead.move':             "Lead bosqichi o'zgartirildi",
  'lead.assign':           "Lead operator o'zgartirildi",
  'lead.convert':          'Lead arizaga aylantirildi',
  'lead.lose':             "Lead yo'qotildi",
  'lead.reopen':           'Lead qayta ochildi',
  'lead.delete':           "Lead o'chirildi",
  'lead.schedule':         'Keyingi aloqa rejalashtirildi',
  'lead.schedule_clear':   "Keyingi aloqa eslatmasi o'chirildi",
}

export const AUDIT_ENTITY_TYPES: Record<string, string> = {
  users:        'Foydalanuvchi',
  applicants:   'Abituriyent',
  applications: 'Ariza',
  contracts:    'Shartnoma',
  payments:     "To'lov",
  diploms:      'Diplom',
  transfer_diploms: 'Perevod diplomi',
  programs:     "Yo'nalish",
  branches:     'Filial',
  leads:        'Lead',
}

/** Returns a category for the given action: create | update | delete | status | other. */
export function auditCategory(action: string): 'create' | 'update' | 'delete' | 'status' | 'other' {
  if (action.endsWith('.create') || action.endsWith('.create_by_staff') || action.endsWith('.create_by_operator')) return 'create'
  if (action.endsWith('.update')) return 'update'
  if (action.endsWith('.delete')) return 'delete'
  if (
    action.endsWith('.sign') || action.endsWith('.cancel') ||
    action.endsWith('.review') || action.endsWith('.start_review') ||
    action.endsWith('.withdraw') || action.endsWith('.confirm') ||
    action.endsWith('.refund') || action.endsWith('.fail') ||
    action.endsWith('.reset_password')
  ) return 'status'
  return 'other'
}

/** Pretty label for a single field name (for the changes diff table). */
export const AUDIT_FIELD_LABELS: Record<string, string> = {
  status:              'Holati',
  rejection_reason:    'Rad etish sababi',
  type:                'Turi',
  application_id:      'Ariza',
  total_amount:        'Jami summa',
  amount:              'Summa',
  reference:           'Reference',
  reason:              'Sabab',
  notes:               'Eslatma',
  approved:            'Qabul qilindi',
  full_name:           'F.I.Sh.',
  phone:               'Telefon',
  email:               'Email',
  role:                'Rol',
  branch_id:           'Filial',
  program_id:          "Yo'nalish",
  education_level_id:  "Ta'lim darajasi",
  education_form_id:   "Ta'lim shakli",
  admission_type:      'Qabul turi',
  signed_at:           'Imzolangan vaqt',
  reviewed_at:         "Ko'rib chiqilgan vaqt",
}

export function fieldLabel(name: string): string {
  return AUDIT_FIELD_LABELS[name] || name
}
