import { http } from '@/api/http'

export interface ProgramRead {
  id: string
  branch_id: string
  education_level_id: string
  education_form_id: string
  name: string
  code: string
  image_id: string | null
  tuition_fee: string
  study_duration: string
  contract_series: string
  is_active: boolean
  created_at: string
  updated_at: string
  // Denormalized via expanded endpoint
  branch_name?: string
  education_level_name?: string
  education_form_name?: string
}

export const programsApi = {
  /** Programs with denormalized branch/level/form names. */
  list: (params: { branch_id?: string; active_only?: boolean } = {}) =>
    http
      .get<ProgramRead[]>('/programs/programs', { params: { active_only: true, ...params } })
      .then((r) => r.data),
}
