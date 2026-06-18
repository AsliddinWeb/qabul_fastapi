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
  yangi_qabul:            '1-kurs (Yangi qabul)',
  perevod:                "O'qishni ko'chirish",
  ikkinchi_mutaxassislik: '2-mutaxassislik',
  magistratura:           'Magistratura',
}

/**
 * Abituriyent CRM funnel statusi — leadlardagidek, lekin sodda.
 * Default 'new'. Shartnoma imzolanganda backend avtomatik
 * 'enrolled'ga o'tkazadi (faqat operator allaqachon 'lost'ga
 * o'rnatmagan bo'lsa).
 */
export const APPLICANT_CONTACT_STATUS: Record<string, string> = {
  new:        'Yangi',
  contacted:  'Gaplashildi',
  interested: 'Qiziqyapti',
  lost:       "Yo'qotildi",
  enrolled:   "O'qishga kirdi",
}

/** Tailwind chip-style class per status — used in lists + detail page. */
export const APPLICANT_CONTACT_STATUS_TONE: Record<string, string> = {
  new:        'bg-slate-100 text-slate-700 dark:bg-slate-700/40 dark:text-slate-300',
  contacted:  'bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300',
  interested: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  lost:       'bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
  enrolled:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
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
  // ===== Middleware-emitted generic actions =====
  // The audit middleware writes one row per successful 2xx mutation using
  // "{entity_type}.{verb}" with the URL segment (plural) as entity_type.
  'applications.create':   'Ariza yaratildi',
  'applications.update':   'Ariza tahrirlandi',
  'applications.delete':   "Ariza o'chirildi",
  'applicants.create':     'Abituriyent yaratildi',
  'applicants.update':     'Abituriyent tahrirlandi',
  'applicants.delete':     "Abituriyent o'chirildi",
  'contracts.create':      'Shartnoma yaratildi',
  'contracts.update':      'Shartnoma tahrirlandi',
  'contracts.delete':      "Shartnoma o'chirildi",
  'payments.create':       "To'lov qo'shildi",
  'payments.update':       "To'lov yangilandi",
  'payments.delete':       "To'lov o'chirildi",
  'leads.create':          'Lead yaratildi',
  'leads.update':          'Lead tahrirlandi',
  'leads.delete':          "Lead o'chirildi",
  'users.create':          'Foydalanuvchi yaratildi',
  'users.update':          'Foydalanuvchi tahrirlandi',
  'users.delete':          "Foydalanuvchi o'chirildi",
  'programs.create':       "Yo'nalish yaratildi",
  'programs.update':       "Yo'nalish tahrirlandi",
  'programs.delete':       "Yo'nalish o'chirildi",
  'auth.login.post':       'Tizimga kirildi',
  'auth.logout.post':      'Tizimdan chiqildi',
  'auth.refresh.post':     'Sessiya yangilandi',
  // Middleware composes "{entity}.{trailing}.{method}" when the URL has a
  // sub-action segment after the entity-id. Map the common ones to friendly
  // Uzbek so the audit log stops showing raw HTTP-style codes.
  'leads.move.post':              "Lead bosqichi o'zgartirildi",
  'leads.assign.post':            "Lead operator o'zgartirildi",
  'leads.comment.post':           'Lead izohi qoʻshildi',
  'leads.call.post':              "Lead qoʻngʻirogʻi qayd etildi",
  'leads.schedule.post':          'Keyingi aloqa rejalashtirildi',
  'leads.lose.post':              "Lead yoʻqotildi",
  'leads.reopen.post':            'Lead qayta ochildi',
  'leads.convert.post':           'Lead arizaga aylantirildi',
  'leads.finalize-conversion.post': 'Lead konversiyasi yakunlandi',
  'leads.public.post':            'Lead yaratildi (saytdan)',
  'contracts.sign.post':          'Shartnoma imzolandi',
  'contracts.cancel.post':        'Shartnoma bekor qilindi',
  'contracts.activate.post':      'Shablon faollashtirildi',
  'applications.review.post':     "Ariza koʻrib chiqildi",
  'applications.start-review.post': "Ariza koʻrib chiqishga olindi",
  'applications.withdraw.post':   'Ariza qaytarib olindi',
  'payments.confirm.post':        "Toʻlov tasdiqlandi",
  'payments.fail.post':           "Toʻlov bajarilmadi",
  'payments.refund.post':         "Toʻlov qaytarildi",
  'users.reset-password.post':    'Parol qayta tiklandi',
  'referrals.apply-to-contract.post': "Referal chegirma qoʻllandi",
  'referrals.payouts.approve.post':   "Naqd toʻlov tasdiqlandi",
  'referrals.payouts.pay.post':       "Naqd toʻlov amalga oshirildi",
  'referrals.payouts.reject.post':    "Naqd toʻlov rad etildi",
}

export const AUDIT_ENTITY_TYPES: Record<string, string> = {
  users:        'Foydalanuvchi',
  applicants:   'Abituriyent',
  applications: 'Ariza',
  contracts:    'Shartnoma',
  payments:     "To'lov",
  diploms:      'Diplom',
  transfer_diploms: "O'qishni ko'chirish diplomi",
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
  application_number:  'Ariza raqami',
  applicant_id:        'Abituriyent ID',
  applicant_full_name: 'Abituriyent F.I.Sh.',
  applicant_phone:     'Abituriyent telefoni',
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
