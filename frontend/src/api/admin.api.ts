import { http } from '@/api/http'
import type { PageResponse } from '@/api/staff.api'
import type { Role, User } from '@/types'

export interface UserRead extends User {
  email: string | null
  is_active: boolean
  is_phone_verified: boolean
  is_consulting?: boolean
  is_root_superadmin?: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface UserCreatePayload {
  phone: string
  full_name?: string | null
  email?: string | null
  role: Role
  password?: string | null
  is_active?: boolean
  is_consulting?: boolean
}

export interface DictionaryTypeRead {
  id: string
  code: string
  name: string
  description: string | null
  is_hierarchical: boolean
  is_system: boolean
}

export interface DictionaryItemPayload {
  code?: string | null
  name_uz: string
  name_ru?: string | null
  name_en?: string | null
  parent_id?: string | null
  sort_order?: number
  is_active?: boolean
}

// ---------- New domain types ----------
export interface NamedRecord {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export interface BranchRead extends NamedRecord {
  is_active: boolean
}

export interface ProgramRead {
  id: string
  branch_id: string
  education_level_id: string
  education_form_id: string
  name: string
  code: string
  image_id: string | null
  tuition_fee: number | string  // Decimal serializes to string from backend; we coerce on frontend
  study_duration_years: number
  contract_series: string
  is_active: boolean
  created_at: string
  updated_at: string
  branch_name?: string
  education_level_name?: string
  education_form_name?: string
}

export interface ProgramCreatePayload {
  branch_id: string
  education_level_id: string
  education_form_id: string
  name: string
  code: string
  tuition_fee: number
  study_duration_years: number
  contract_series: string
  is_active?: boolean
  image_id?: string | null
}

export interface CountryRead extends NamedRecord {}
export interface RegionRead extends NamedRecord { country_id: string }
export interface DistrictRead extends NamedRecord { region_id: string }

export const adminApi = {
  users: {
    list: (filters: { role?: string; is_active?: boolean; search?: string; page?: number; size?: number } = {}) =>
      http.get<PageResponse<UserRead>>('/users', { params: filters }).then((r) => r.data),
    get: (id: string) => http.get<UserRead>(`/users/${id}`).then((r) => r.data),
    create: (payload: UserCreatePayload) =>
      http.post<UserRead>('/users', payload).then((r) => r.data),
    update: (id: string, payload: Partial<UserCreatePayload>) =>
      http.patch<UserRead>(`/users/${id}`, payload).then((r) => r.data),
    resetPassword: (id: string, new_password: string) =>
      http.post<UserRead>(`/users/${id}/password`, { new_password }).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/users/${id}`).then((r) => r.data),
  },

  dictionaries: {
    types: () =>
      http.get<DictionaryTypeRead[]>('/dictionaries/types').then((r) => r.data),
    items: (type_code: string, parent_id?: string) =>
      http
        .get<any[]>('/dictionaries/items', { params: { type_code, parent_id, active_only: false } })
        .then((r) => r.data),
    addItem: (type_id: string, payload: DictionaryItemPayload) =>
      http.post(`/dictionaries/types/${type_id}/items`, payload).then((r) => r.data),
    updateItem: (item_id: string, payload: Partial<DictionaryItemPayload>) =>
      http.patch(`/dictionaries/items/${item_id}`, payload).then((r) => r.data),
    deleteItem: (item_id: string) =>
      http.delete(`/dictionaries/items/${item_id}`).then((r) => r.data),
  },

  // ---------- Programs (Branch / Edu* / Program) ----------
  branches: {
    list: (active_only = false) =>
      http.get<BranchRead[]>('/programs/branches', { params: { active_only } }).then((r) => r.data),
    create: (payload: { name: string; is_active?: boolean }) =>
      http.post<BranchRead>('/programs/branches', payload).then((r) => r.data),
    update: (id: string, payload: Partial<{ name: string; is_active: boolean }>) =>
      http.patch<BranchRead>(`/programs/branches/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/programs/branches/${id}`).then((r) => r.data),
  },

  educationLevels: {
    list: () =>
      http.get<NamedRecord[]>('/programs/education-levels').then((r) => r.data),
    create: (payload: { name: string }) =>
      http.post<NamedRecord>('/programs/education-levels', payload).then((r) => r.data),
    update: (id: string, payload: { name: string }) =>
      http.patch<NamedRecord>(`/programs/education-levels/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/programs/education-levels/${id}`).then((r) => r.data),
  },

  educationForms: {
    list: () =>
      http.get<NamedRecord[]>('/programs/education-forms').then((r) => r.data),
    create: (payload: { name: string }) =>
      http.post<NamedRecord>('/programs/education-forms', payload).then((r) => r.data),
    update: (id: string, payload: { name: string }) =>
      http.patch<NamedRecord>(`/programs/education-forms/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/programs/education-forms/${id}`).then((r) => r.data),
  },

  programs: {
    list: (params: { branch_id?: string; active_only?: boolean } = {}) =>
      http.get<ProgramRead[]>('/programs/programs', { params: { active_only: false, ...params } }).then((r) => r.data),
    get: (id: string) =>
      http.get<ProgramRead>(`/programs/programs/${id}`).then((r) => r.data),
    create: (payload: ProgramCreatePayload) =>
      http.post<ProgramRead>('/programs/programs', payload).then((r) => r.data),
    update: (id: string, payload: Partial<ProgramCreatePayload>) =>
      http.patch<ProgramRead>(`/programs/programs/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/programs/programs/${id}`).then((r) => r.data),
  },

  // ---------- Geo ----------
  countries: {
    list: () => http.get<CountryRead[]>('/regions/countries').then((r) => r.data),
    create: (payload: { name: string }) =>
      http.post<CountryRead>('/regions/countries', payload).then((r) => r.data),
    update: (id: string, payload: { name: string }) =>
      http.patch<CountryRead>(`/regions/countries/${id}`, payload).then((r) => r.data),
    delete: (id: string) => http.delete(`/regions/countries/${id}`).then((r) => r.data),
  },

  regions: {
    list: (country_id?: string) =>
      http.get<RegionRead[]>('/regions/regions', { params: { country_id } }).then((r) => r.data),
    create: (payload: { name: string; country_id: string }) =>
      http.post<RegionRead>('/regions/regions', payload).then((r) => r.data),
    update: (id: string, payload: Partial<{ name: string; country_id: string }>) =>
      http.patch<RegionRead>(`/regions/regions/${id}`, payload).then((r) => r.data),
    delete: (id: string) => http.delete(`/regions/regions/${id}`).then((r) => r.data),
  },

  districts: {
    list: (region_id?: string) =>
      http.get<DistrictRead[]>('/regions/districts', { params: { region_id } }).then((r) => r.data),
    create: (payload: { name: string; region_id: string }) =>
      http.post<DistrictRead>('/regions/districts', payload).then((r) => r.data),
    update: (id: string, payload: Partial<{ name: string; region_id: string }>) =>
      http.patch<DistrictRead>(`/regions/districts/${id}`, payload).then((r) => r.data),
    delete: (id: string) => http.delete(`/regions/districts/${id}`).then((r) => r.data),
  },

  // ---------- Diploms catalog ----------
  educationTypes: {
    list: () => http.get<NamedRecord[]>('/applicants/catalog/education-types').then((r) => r.data),
    create: (payload: { name: string }) =>
      http.post<NamedRecord>('/applicants/catalog/education-types', payload).then((r) => r.data),
    update: (id: string, payload: { name: string }) =>
      http.patch<NamedRecord>(`/applicants/catalog/education-types/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/applicants/catalog/education-types/${id}`).then((r) => r.data),
  },

  institutionTypes: {
    list: () => http.get<NamedRecord[]>('/applicants/catalog/institution-types').then((r) => r.data),
    create: (payload: { name: string }) =>
      http.post<NamedRecord>('/applicants/catalog/institution-types', payload).then((r) => r.data),
    update: (id: string, payload: { name: string }) =>
      http.patch<NamedRecord>(`/applicants/catalog/institution-types/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/applicants/catalog/institution-types/${id}`).then((r) => r.data),
  },

  courses: {
    list: () => http.get<NamedRecord[]>('/applicants/catalog/courses').then((r) => r.data),
    create: (payload: { name: string }) =>
      http.post<NamedRecord>('/applicants/catalog/courses', payload).then((r) => r.data),
    update: (id: string, payload: { name: string }) =>
      http.patch<NamedRecord>(`/applicants/catalog/courses/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/applicants/catalog/courses/${id}`).then((r) => r.data),
  },

  // ---------- Diploms (1-kurs) ----------
  diploms: {
    list: (params: { user_id?: string; search?: string; page?: number; size?: number } = {}) =>
      http.get<PageResponse<any>>('/applicants/diploms', { params }).then((r) => r.data),
    get: (id: string) =>
      http.get<any>(`/applicants/diploms/${id}`).then((r) => r.data),
    create: (payload: any) =>
      http.post<any>('/applicants/diploms', payload).then((r) => r.data),
    update: (id: string, payload: any) =>
      http.patch<any>(`/applicants/diploms/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/applicants/diploms/${id}`).then((r) => r.data),
  },

  // ---------- Transfer diploms (perevod) ----------
  transferDiploms: {
    list: (params: { user_id?: string; country_id?: string; search?: string; page?: number; size?: number } = {}) =>
      http.get<PageResponse<any>>('/applicants/transfer-diploms', { params }).then((r) => r.data),
    get: (id: string) =>
      http.get<any>(`/applicants/transfer-diploms/${id}`).then((r) => r.data),
    create: (payload: any) =>
      http.post<any>('/applicants/transfer-diploms', payload).then((r) => r.data),
    update: (id: string, payload: any) =>
      http.patch<any>(`/applicants/transfer-diploms/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/applicants/transfer-diploms/${id}`).then((r) => r.data),
  },

  // ---------- Applicants (admin: full CRUD) ----------
  applicants: {
    list: (params: { region_id?: string; search?: string; page?: number; size?: number } = {}) =>
      http.get<PageResponse<any>>('/applicants', { params }).then((r) => r.data),
    get: (id: string) => http.get<any>(`/applicants/${id}`).then((r) => r.data),
    create: (payload: any) =>
      http.post<any>('/applicants', payload).then((r) => r.data),
    update: (id: string, payload: any) =>
      http.patch<any>(`/applicants/${id}`, payload).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/applicants/${id}`).then((r) => r.data),
  },

  // ---------- Applications (admin: full CRUD) ----------
  applications: {
    list: (params: {
      status?: string; admission_type?: string;
      program_id?: string; branch_id?: string;
      education_level_id?: string; education_form_id?: string;
      consulting_agency_id?: string;
      page?: number; size?: number;
    } = {}) =>
      http.get<PageResponse<any>>('/applications', { params }).then((r) => r.data),
    stats: () => http.get<Record<string, number>>('/applications/stats').then((r) => r.data),
    trend: (months = 12) => http.get<Array<{ month: string; topshirildi: number; korib_chiqilmoqda: number; qabul_qilindi: number; rad_etildi: number; total: number }>>('/applications/trend', { params: { months } }).then((r) => r.data),
    get: (id: string) =>
      http.get<any>(`/applications/${id}`).then((r) => r.data),
    create: (payload: any) =>
      http.post<any>('/applications', payload).then((r) => r.data),
    update: (id: string, payload: any) =>
      http.patch<any>(`/applications/${id}`, payload).then((r) => r.data),
    review: (id: string, payload: { approved: boolean; rejection_reason?: string }) =>
      http.post<any>(`/applications/${id}/review`, payload).then((r) => r.data),
    startReview: (id: string) =>
      http.post<any>(`/applications/${id}/start-review`).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/applications/${id}`).then((r) => r.data),
  },

  // ---------- Contracts (admin) ----------
  contracts: {
    list: (params: { status?: string; type?: string; search?: string; page?: number; size?: number } = {}) =>
      http.get<PageResponse<any>>('/contracts', { params }).then((r) => r.data),
    get: (id: string) =>
      http.get<any>(`/contracts/${id}`).then((r) => r.data),
    sign: (id: string) =>
      http.post<any>(`/contracts/${id}/sign`, { notes: null }).then((r) => r.data),
    cancel: (id: string) =>
      http.post<any>(`/contracts/${id}/cancel`).then((r) => r.data),
    openPdf: async (id: string) => {
      const res = await http.get(`/contracts/${id}/pdf`, { responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)

      // Pull filename from Content-Disposition (RFC 5987) so the
      // browser's "Save As" uses e.g. ABDUJABBOROV-ASLIDDIN.pdf
      const cd = (res.headers as any)['content-disposition'] as string | undefined
      let filename = `contract-${id}.pdf`
      if (cd) {
        const star = /filename\*\s*=\s*[^']*''([^;]+)/i.exec(cd)
        const plain = /filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;]+)/i.exec(cd)
        if (star?.[1]) {
          try { filename = decodeURIComponent(star[1]) } catch { /* keep default */ }
        } else if (plain) {
          filename = (plain[1] || plain[2] || '').trim()
        }
      }

      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.target = '_blank'
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    },
  },

  // ---------- Payments (admin) ----------
  payments: {
    list: (params: { status?: string; contract_id?: string; page?: number; size?: number } = {}) =>
      http.get<PageResponse<any>>('/payments', { params }).then((r) => r.data),
    listForContract: (contract_id: string) =>
      http.get<any[]>(`/payments/contracts/${contract_id}`).then((r) => r.data),
    confirm: (id: string, payload: any = {}) =>
      http.post<any>(`/payments/${id}/confirm`, payload).then((r) => r.data),
    fail: (id: string, reason?: string) =>
      http.post<any>(`/payments/${id}/fail`, null, { params: { reason } }).then((r) => r.data),
    refund: (id: string, reason?: string) =>
      http.post<any>(`/payments/${id}/refund`, null, { params: { reason } }).then((r) => r.data),
  },
}
