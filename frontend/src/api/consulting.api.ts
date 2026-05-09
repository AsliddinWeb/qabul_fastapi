import { http } from '@/api/http'

export interface ConsultingAgency {
  id: string
  name: string
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ConsultingAgencyPayload {
  name: string
  is_active?: boolean
  notes?: string | null
}

export const consultingApi = {
  list: (activeOnly = false) =>
    http.get<ConsultingAgency[]>('/consulting-agencies', {
      params: { active_only: activeOnly },
    }).then((r) => r.data),

  create: (payload: ConsultingAgencyPayload) =>
    http.post<ConsultingAgency>('/consulting-agencies', payload).then((r) => r.data),

  update: (id: string, payload: Partial<ConsultingAgencyPayload>) =>
    http.patch<ConsultingAgency>(`/consulting-agencies/${id}`, payload).then((r) => r.data),

  delete: (id: string) =>
    http.delete(`/consulting-agencies/${id}`).then((r) => r.data),
}
