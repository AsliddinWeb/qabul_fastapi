import { http } from '@/api/http'

export type PaymentStatus = 'pending' | 'confirmed' | 'failed' | 'refunded'

export interface PaymentRead {
  id: string
  payment_number: string
  contract_id: string
  amount: string
  currency: string
  payment_method_id: string
  status: PaymentStatus
  paid_at: string | null
  reference: string | null
  receipt_file_id?: string | null
  registered_by_id?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface PaymentCreatePayload {
  contract_id: string
  amount: number | string
  currency?: string
  payment_method_id: string
  reference?: string | null
  notes?: string | null
  receipt_file_id?: string | null
}

export interface PaymentConfirmPayload {
  paid_at?: string | null
  reference?: string | null
}

export interface AccountantDebtor {
  contract_id: string
  contract_number: string
  applicant_full_name: string
  total_amount: string
  paid_amount: string
  balance: string
}

export interface PaymentListParams {
  status?: PaymentStatus
  contract_id?: string
  payment_method_id?: string
  date_from?: string
  date_to?: string
  page?: number
  size?: number
}

export interface PaymentListResponse {
  items: PaymentRead[]
  total: number
  page: number
  size: number
}

export interface PaymentsBreakdown {
  period_count: number
  period_sum: string
  by_method: Array<{ method_id: string; method_name: string; count: number; sum: string }>
  by_branch: Array<{ branch_id: string; branch_name: string; count: number; sum: string }>
}

export interface AccountantDashboardResponse {
  today_count: number
  today_sum: string
  month_count: number
  month_sum: string
  pending_count: number
  pending_sum: string
  outstanding_total: string
  monthly_trend: Array<{ month: string; count: number; sum: string }>
  top_debtors: AccountantDebtor[]
}

export const paymentsApi = {
  forContract: (contractId: string) =>
    http.get<PaymentRead[]>(`/payments/contracts/${contractId}`).then((r) => r.data),

  create: (payload: PaymentCreatePayload) =>
    http.post<PaymentRead>('/payments', payload).then((r) => r.data),

  confirm: (id: string, payload: PaymentConfirmPayload = {}) =>
    http.post<PaymentRead>(`/payments/${id}/confirm`, payload).then((r) => r.data),

  fail: (id: string, reason?: string) =>
    http
      .post<PaymentRead>(`/payments/${id}/fail`, undefined, { params: { reason } })
      .then((r) => r.data),

  refund: (id: string, reason?: string) =>
    http
      .post<PaymentRead>(`/payments/${id}/refund`, undefined, { params: { reason } })
      .then((r) => r.data),

  // Applicant self-service: own payments (read-only)
  myList: () =>
    http.get<PaymentRead[]>('/payments/me').then((r) => r.data),

  dashboard: () =>
    http.get<AccountantDashboardResponse>('/payments/dashboard').then((r) => r.data),

  list: (params: PaymentListParams = {}) =>
    http.get<PaymentListResponse>('/payments', { params }).then((r) => r.data),

  breakdown: (params: { date_from?: string; date_to?: string } = {}) =>
    http.get<PaymentsBreakdown>('/payments/breakdown', { params }).then((r) => r.data),
}
