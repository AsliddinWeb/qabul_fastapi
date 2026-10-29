import { http } from './http'

export interface Voucher {
  id: string
  voucher_number: number
  number: string            // "0001"
  application_id: string
  contract_id: string | null
  discount_percent: number
  student_full_name: string
  program_name: string
  valid_until: string       // YYYY-MM-DD
  status: 'active' | 'cancelled'
  created_by_id: string | null
  created_at: string
  cancelled_at: string | null
  cancelled_by_id: string | null
  cancelled_reason: string | null
}

export const vouchersApi = {
  defaults: () =>
    http.get<{ valid_until: string; discount_percent: number }>('/vouchers/defaults').then((r) => r.data),

  list: (applicationId: string) =>
    http.get<Voucher[]>('/vouchers', { params: { application_id: applicationId } }).then((r) => r.data),

  issue: (applicationId: string, validUntil?: string) =>
    http.post<Voucher>('/vouchers', {
      application_id: applicationId,
      valid_until: validUntil || null,
    }).then((r) => r.data),

  cancel: (id: string, reason?: string) =>
    http.post<Voucher>(`/vouchers/${id}/cancel`, { reason: reason || null }).then((r) => r.data),

  /** Open the rendered PDF in a new tab (falls back to download). */
  openPdf: async (id: string) => {
    const res = await http.get(`/vouchers/${id}/pdf`, { responseType: 'blob', timeout: 60_000 })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const win = window.open(url, '_blank')
    if (!win) {
      const a = document.createElement('a')
      a.href = url
      a.download = `vaucher-${id}.pdf`
      a.click()
    }
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  },
}
