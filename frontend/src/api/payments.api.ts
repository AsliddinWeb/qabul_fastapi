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
}

export interface PaymentConfirmPayload {
  paid_at?: string | null
  reference?: string | null
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
}
