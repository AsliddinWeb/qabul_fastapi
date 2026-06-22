/**
 * International admissions API client.
 *
 * The public /apply submission lives in the standalone landing page —
 * this module only covers the staff-facing endpoints (list, detail,
 * stage advance/regress, reject/unreject, notes, delete).
 */
import { http } from '@/api/http'
import type { PageResponse } from '@/api/staff.api'

export interface IntlApplicationListItem {
  id: string
  ref_number: string
  full_name: string
  country: string
  passport_number: string
  program: string
  faculty_text: string
  phone: string
  email: string
  stage: number
  rejected: boolean
  created_at: string
  updated_at: string
}

export interface IntlApplication extends IntlApplicationListItem {
  birth_date: string
  faculty_code: string
  passport_file_id: string | null
  diploma_file_id: string | null
  photo_file_id: string | null
  rejection_reason: string | null
  notes: string | null
  language: string | null
  submitter_ip: string | null
  submitter_user_agent: string | null
}

export interface IntlStageCounts {
  stage_0: number
  stage_1: number
  stage_2: number
  stage_3: number
  stage_4: number
  stage_5: number
  rejected: number
  total: number
}

export const STAGE_LABELS: string[] = [
  'Ariza topshirildi',
  'Hujjat tekshiruvi',
  'Shartli taklif',
  'Shartnoma imzolandi',
  "To'lov qabul qilindi",
  "Qabul qilindi va taklif etildi",
]

export const STAGE_TONES: string[] = [
  'bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700/60',
  'bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-500/15 dark:text-blue-300 dark:ring-blue-700/40',
  'bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-500/15 dark:text-violet-300 dark:ring-violet-700/40',
  'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-700/40',
  'bg-cyan-50 text-cyan-700 ring-cyan-200 dark:bg-cyan-500/15 dark:text-cyan-300 dark:ring-cyan-700/40',
  'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-700/40',
]

export const internationalApi = {
  list: (params: {
    stage?: number
    country?: string
    rejected?: boolean
    search?: string
    page?: number
    size?: number
  } = {}) =>
    http.get<PageResponse<IntlApplicationListItem>>('/international-admissions', { params })
      .then(r => r.data),

  stats: () =>
    http.get<IntlStageCounts>('/international-admissions/stats').then(r => r.data),

  get: (id: string) =>
    http.get<IntlApplication>(`/international-admissions/${id}`).then(r => r.data),

  advance: (id: string, direction: 'next' | 'back') =>
    http.patch<IntlApplication>(`/international-admissions/${id}/stage`, { direction })
      .then(r => r.data),

  reject: (id: string, reason?: string) =>
    http.patch<IntlApplication>(`/international-admissions/${id}/reject`, { reason })
      .then(r => r.data),

  unreject: (id: string) =>
    http.patch<IntlApplication>(`/international-admissions/${id}/unreject`).then(r => r.data),

  updateNotes: (id: string, notes: string | null) =>
    http.patch<IntlApplication>(`/international-admissions/${id}/notes`, { notes })
      .then(r => r.data),

  delete: (id: string) =>
    http.delete(`/international-admissions/${id}`).then(r => r.data),
}
