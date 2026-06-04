import { http } from '@/api/http'
import type { PageResponse } from '@/api/staff.api'

export type LeadStatus = 'open' | 'won' | 'lost'

export interface LeadPipeline {
  id: string
  name: string
  description: string | null
  is_default: boolean
  is_active: boolean
  order_index: number
  created_at: string
}

export interface LeadStage {
  id: string
  pipeline_id: string
  name: string
  order_index: number
  color: string | null
  is_terminal: boolean
  is_active: boolean
}

export interface LeadSource {
  id: string
  code: string
  name: string
  is_active: boolean
  order_index: number
}

export interface LeadLostReason {
  id: string
  name: string
  is_active: boolean
  order_index: number
}

export interface Lead {
  id: string
  full_name: string
  phone: string
  email: string | null
  telegram_username: string | null
  pipeline_id: string
  stage_id: string
  source_id: string | null
  source_meta: Record<string, any> | null
  branch_id: string | null
  program_id: string | null
  assigned_to_id: string | null
  created_by_id: string | null
  notes: string | null
  status: LeadStatus
  applicant_id: string | null
  application_id: string | null
  converted_at: string | null
  lost_reason_id: string | null
  lost_comment: string | null
  lost_at: string | null
  last_contact_at: string | null
  next_contact_at: string | null
  next_contact_note: string | null
  stage_entered_at: string
  created_at: string
  updated_at: string
  // embedded labels
  stage_name: string | null
  stage_color: string | null
  pipeline_name: string | null
  source_name: string | null
  source_code: string | null
  branch_name: string | null
  program_name: string | null
  assigned_to_name: string | null
}

export interface LeadActivity {
  id: string
  lead_id: string
  user_id: string | null
  user_full_name: string | null
  user_phone: string | null
  action: string
  from_stage_id: string | null
  from_stage_name: string | null
  to_stage_id: string | null
  to_stage_name: string | null
  comment: string | null
  extra: Record<string, any> | null
  created_at: string
}

export interface LeadBoardStage {
  id: string
  name: string
  color: string | null
  is_terminal: boolean
  order_index: number
  leads: Lead[]
}

export interface LeadBoardResponse {
  pipeline_id: string
  pipeline_name: string
  stages: LeadBoardStage[]
}

export interface LeadStats {
  pipeline_id: string
  pipeline_name: string
  total: number
  open: number
  won: number
  lost: number
  conversion_rate: number
  by_stage: Array<{ stage_id: string; name: string; order_index: number; open_leads: number }>
}

export interface LeadCreatePayload {
  full_name: string
  phone: string
  email?: string | null
  telegram_username?: string | null
  pipeline_id?: string | null
  stage_id?: string | null
  source_id?: string | null
  source_meta?: Record<string, any> | null
  branch_id?: string | null
  program_id?: string | null
  assigned_to_id?: string | null
  auto_assign?: boolean
  notes?: string | null
}

export interface LeadPrefill {
  lead_id: string
  phone: string
  email: string | null
  telegram_username: string | null
  last_name: string
  first_name: string
  other_name: string
  branch_id: string | null
  program_id: string | null
  source_code: string | null
  notes: string | null
}

export const leadsApi = {
  // ---- core ----
  list: (params: {
    pipeline_id?: string; stage_id?: string; status?: string;
    source_id?: string; assigned_to_id?: string; branch_id?: string;
    search?: string; page?: number; size?: number;
  } = {}) =>
    http.get<PageResponse<Lead>>('/leads', { params }).then(r => r.data),

  get: (id: string) => http.get<Lead>(`/leads/${id}`).then(r => r.data),
  create: (payload: LeadCreatePayload) =>
    http.post<{ lead: Lead; merged: boolean }>('/leads', payload).then(r => r.data),
  // Pre-submit dedup probe. Returns existence + who owns the existing
  // OPEN lead. Used by LeadNewPage to warn before submit.
  checkPhone: (phone: string) =>
    http.get<{
      exists: boolean
      lead_id?: string
      full_name?: string
      assigned_to_id?: string | null
      assigned_to_name?: string | null
      stage_name?: string | null
    }>('/leads/check-phone', { params: { phone } }).then(r => r.data),
  update: (id: string, payload: Partial<LeadCreatePayload>) => http.patch<Lead>(`/leads/${id}`, payload).then(r => r.data),
  delete: (id: string) => http.delete(`/leads/${id}`).then(r => r.data),
  bulkDelete: (ids: string[]) =>
    http.post<{ deleted: number; skipped: number }>('/leads/bulk-delete', { ids }).then(r => r.data),
  bulkAssign: (ids: string[], user_id: string | null) =>
    http.post<{ assigned: number; skipped: number }>('/leads/bulk-assign', { ids, user_id }).then(r => r.data),

  move: (id: string, stage_id: string, comment?: string) =>
    http.post<Lead>(`/leads/${id}/move`, { stage_id, comment }).then(r => r.data),
  assign: (id: string, payload: { user_id?: string | null; auto_assign?: boolean }) =>
    http.post<Lead>(`/leads/${id}/assign`, payload).then(r => r.data),
  comment: (id: string, comment: string) =>
    http.post<LeadActivity>(`/leads/${id}/comment`, { comment }).then(r => r.data),
  logCall: (id: string, comment?: string) =>
    http.post<LeadActivity>(`/leads/${id}/call`, { comment: comment || null }).then(r => r.data),
  schedule: (id: string, payload: { next_contact_at: string | null; note?: string | null }) =>
    http.post<Lead>(`/leads/${id}/schedule`, payload).then(r => r.data),
  lose: (id: string, payload: { reason_id?: string | null; comment?: string }) =>
    http.post<Lead>(`/leads/${id}/lose`, payload).then(r => r.data),
  reopen: (id: string) => http.post<Lead>(`/leads/${id}/reopen`).then(r => r.data),

  prefill: (id: string) => http.get<LeadPrefill>(`/leads/${id}/prefill`).then(r => r.data),
  finalizeConversion: (id: string, applicant_id: string, application_id: string) =>
    http.post<Lead>(`/leads/${id}/finalize-conversion`, { applicant_id, application_id }).then(r => r.data),

  activities: (id: string) => http.get<LeadActivity[]>(`/leads/${id}/activities`).then(r => r.data),
  relatedApplications: (id: string) =>
    http.get<{
      user_id: string | null
      applications: Array<{
        id: string
        application_number: string
        status: string | null
        admission_type: string | null
        program_name: string | null
        branch_name: string | null
        created_at: string | null
        submitted_at: string | null
      }>
    }>(`/leads/${id}/related-applications`).then(r => r.data),
  board: (pipeline_id?: string) =>
    http.get<LeadBoardResponse>('/leads/board', { params: { pipeline_id } }).then(r => r.data),
  stats: (pipeline_id?: string, assigned_to_id?: string) =>
    http.get<LeadStats>('/leads/stats', { params: { pipeline_id, assigned_to_id } }).then(r => r.data),
  slaAlerts: (within_hours = 24) =>
    http.get<Array<Lead & { last_alert_at: string | null }>>('/leads/sla-alerts', { params: { within_hours } }).then(r => r.data),
  breakdown: () =>
    http.get<{
      by_source: Array<{ source_id: string; name: string; total: number; won: number; lost: number; open: number; conversion_rate: number }>;
      by_operator: Array<{ user_id: string; name: string; phone: string; total: number; won: number; lost: number; open: number; conversion_rate: number }>;
    }>('/leads/stats/breakdown').then(r => r.data),
  exportCsv: async (params: Record<string, any> = {}) => {
    const res = await http.get('/leads/export.csv', { params, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const cd = (res.headers as any)['content-disposition'] as string | undefined
    const m = cd?.match(/filename="?([^";]+)"?/i)
    a.href = url; a.download = m?.[1] || `leads-${new Date().toISOString().slice(0,16).replace(/[:T]/g,'-')}.csv`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  },

  // ---- catalog ----
  pipelines: {
    list: () => http.get<LeadPipeline[]>('/leads/catalog/pipelines').then(r => r.data),
    create: (payload: Partial<LeadPipeline>) => http.post<LeadPipeline>('/leads/catalog/pipelines', payload).then(r => r.data),
    update: (id: string, payload: Partial<LeadPipeline>) => http.patch<LeadPipeline>(`/leads/catalog/pipelines/${id}`, payload).then(r => r.data),
    delete: (id: string) => http.delete(`/leads/catalog/pipelines/${id}`).then(r => r.data),
  },
  stages: {
    list: (pipeline_id: string) => http.get<LeadStage[]>('/leads/catalog/stages', { params: { pipeline_id } }).then(r => r.data),
    create: (payload: Partial<LeadStage>) => http.post<LeadStage>('/leads/catalog/stages', payload).then(r => r.data),
    update: (id: string, payload: Partial<LeadStage>) => http.patch<LeadStage>(`/leads/catalog/stages/${id}`, payload).then(r => r.data),
    delete: (id: string) => http.delete(`/leads/catalog/stages/${id}`).then(r => r.data),
  },
  sources: {
    list: () => http.get<LeadSource[]>('/leads/catalog/sources').then(r => r.data),
    create: (payload: Partial<LeadSource>) => http.post<LeadSource>('/leads/catalog/sources', payload).then(r => r.data),
    update: (id: string, payload: Partial<LeadSource>) => http.patch<LeadSource>(`/leads/catalog/sources/${id}`, payload).then(r => r.data),
    delete: (id: string) => http.delete(`/leads/catalog/sources/${id}`).then(r => r.data),
  },
  lostReasons: {
    list: () => http.get<LeadLostReason[]>('/leads/catalog/lost-reasons').then(r => r.data),
    create: (payload: Partial<LeadLostReason>) => http.post<LeadLostReason>('/leads/catalog/lost-reasons', payload).then(r => r.data),
    update: (id: string, payload: Partial<LeadLostReason>) => http.patch<LeadLostReason>(`/leads/catalog/lost-reasons/${id}`, payload).then(r => r.data),
    delete: (id: string) => http.delete(`/leads/catalog/lost-reasons/${id}`).then(r => r.data),
  },
}
