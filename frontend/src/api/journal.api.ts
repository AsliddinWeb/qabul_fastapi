import { http, downloadFile } from './http'

export type JournalCode =
  | 'registered'
  | 'registered_by_staff'
  | 'application_submitted'
  | 'status_changed'
  | 'contract_created'
  | 'contract_renewed'
  | 'contract_signed'
  | 'contract_cancelled'

export interface JournalItem {
  at: string
  applicant_id: string
  application_id: string | null
  full_name: string
  pinfl: string
  phone: string
  code: JournalCode
  event: string
  detail: string
  program: string
  application_number: string
  contract_number: string
  actor: string
}

export interface JournalPage {
  items: JournalItem[]
  total: number
  page: number
  size: number
  stats: Record<JournalCode, number>
  labels: Record<JournalCode, string>
}

export interface JournalFilters {
  date_from?: string
  date_to?: string
  search?: string
  codes?: string
}

export const journalApi = {
  list: (params: JournalFilters & { page?: number; size?: number }) =>
    http.get<JournalPage>('/journal', { params }).then((r) => r.data),

  exportXlsx: (view: 'dates' | 'applicants', params: JournalFilters) =>
    downloadFile('/journal/export.xlsx', { view, ...params }, {
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      fallbackName: `tizim-daftari-${view}.xlsx`,
      timeout: 180_000,
    }),
}
