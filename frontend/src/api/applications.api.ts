import { http } from '@/api/http'

export type ApplicationStatus =
  | 'topshirildi' | 'korib_chiqilmoqda' | 'qabul_qilindi' | 'rad_etildi'

export type AdmissionType = 'yangi_qabul' | 'perevod'

export const APPLICATION_STATUS_LABEL: Record<ApplicationStatus, string> = {
  topshirildi: 'Topshirildi',
  korib_chiqilmoqda: "Ko'rib chiqilmoqda",
  qabul_qilindi: 'Qabul qilindi',
  rad_etildi: 'Rad etildi',
}

export const ADMISSION_TYPE_LABEL: Record<AdmissionType, string> = {
  yangi_qabul: '1-kurs (Yangi qabul)',
  perevod: 'Perevod',
}

export interface ApplicationDetailed {
  id: string
  application_number: string
  applicant_id: string
  admission_type: AdmissionType
  branch_id: string
  education_level_id: string
  education_form_id: string
  program_id: string
  diplom_id: string | null
  transfer_diplom_id: string | null
  course_id: string | null
  contract_file_id: string | null
  status: ApplicationStatus
  submitted_at: string | null
  reviewed_by_id?: string | null
  reviewed_at?: string | null
  rejection_reason?: string | null
  notes?: string | null
  created_at: string
  updated_at: string

  // Denormalized (server joins)
  program_name?: string | null
  program_code?: string | null
  branch_name?: string | null
  education_level_name?: string | null
  education_form_name?: string | null
  applicant_full_name?: string | null
}

export const applicationsApi = {
  myList: () => http.get<ApplicationDetailed[]>('/applications/me').then((r) => r.data),

  submit: (payload: {
    admission_type: AdmissionType
    branch_id: string
    education_level_id: string
    education_form_id: string
    program_id: string
    diplom_id?: string | null
    transfer_diplom_id?: string | null
    course_id?: string | null
    notes?: string | null
  }) =>
    http
      .post<ApplicationDetailed>('/applications/me', payload)
      .then((r) => r.data),

  withdraw: (id: string) =>
    http.post<ApplicationDetailed>(`/applications/me/${id}/withdraw`).then((r) => r.data),
}
