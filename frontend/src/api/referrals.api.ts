import { http } from '@/api/http'

export type ReferralStatus =
  | 'pending'
  | 'active'
  | 'spent_on_contract'
  | 'paid_cash'
  | 'cancelled'

export interface ReferralCode {
  referral_code: string
  share_url: string
}

export interface ReferralRead {
  id: string
  referrer_user_id: string
  referred_applicant_id: string
  contract_id: string | null
  status: ReferralStatus
  reward_amount: string
  source: 'link' | 'manual'
  activated_at: string | null
  cancelled_at: string | null
  payout_at: string | null
  applied_contract_id: string | null
  cash_payout_id: string | null
  cancelled_reason: string | null
  notes: string | null
  referred_full_name: string | null
  created_at: string
  updated_at: string
}

export interface ReferralSettings {
  id: string
  reward_amount: string
  qualification_percent: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ReferralAvailableBalance {
  active_count: number
  earmarked_count: number
  available_count: number
  available_amount: string
}

export interface TopReferrer {
  user_id: string
  full_name: string | null
  phone: string | null
  referral_code: string | null
  total_invited: number
  active_count: number
  spent_count: number
  paid_count: number
  earned_amount: string
}

export interface ReferralStats {
  total_referrals: number
  by_status: Record<string, number>
  total_discount_amount: string
  total_cash_paid: string
  cash_pending_count: number
  cash_pending_amount: string
  top_referrers: TopReferrer[]
  monthly_trend: Array<{ month: string; count: number }>
}

export interface ReferralPayoutRead {
  id: string
  referrer_user_id: string
  amount: string
  referral_count: number
  status: 'requested' | 'approved' | 'paid' | 'rejected'
  requested_at: string
  approved_by_user_id: string | null
  approved_at: string | null
  paid_at: string | null
  rejected_reason: string | null
  notes: string | null
  referrer_full_name: string | null
  referrer_phone: string | null
  created_at: string
  updated_at: string
}

export const referralsApi = {
  // Current user
  myCode: () => http.get<ReferralCode>('/referrals/me/code').then(r => r.data),
  mine: (status?: ReferralStatus) =>
    http.get<ReferralRead[]>('/referrals/me', {
      params: status ? { status_filter: status } : undefined,
    }).then(r => r.data),

  // Staff
  list: (params: {
    status_filter?: ReferralStatus
    referrer_user_id?: string
    referred_applicant_id?: string
  } = {}) =>
    http.get<ReferralRead[]>('/referrals', { params }).then(r => r.data),

  attach: (applicantId: string, referrerCode: string) =>
    http.post<ReferralRead>(
      `/referrals/applicants/${applicantId}/attach`,
      { referrer_code: referrerCode },
    ).then(r => r.data),

  detach: (applicantId: string) =>
    http.delete(`/referrals/applicants/${applicantId}/attach`).then(r => r.data),

  // Admin
  settings: () => http.get<ReferralSettings>('/referrals/settings').then(r => r.data),

  // Phase 4 — redemption
  available: () =>
    http.get<ReferralAvailableBalance>('/referrals/me/available').then(r => r.data),

  applyToContract: (contractId: string, count: number) =>
    http.post<{
      count: number
      discount: string
      contract_id: string
      new_total_amount: string
    }>('/referrals/apply-to-contract', { contract_id: contractId, count }).then(r => r.data),

  requestCash: (count: number, notes?: string) =>
    http.post<ReferralPayoutRead>('/referrals/me/cash-payout', { count, notes: notes || null })
      .then(r => r.data),

  myPayouts: () => http.get<ReferralPayoutRead[]>('/referrals/me/payouts').then(r => r.data),

  // Accountant / admin
  payouts: (statusFilter?: ReferralPayoutRead['status']) =>
    http.get<ReferralPayoutRead[]>('/referrals/payouts', {
      params: statusFilter ? { status_filter: statusFilter } : undefined,
    }).then(r => r.data),

  approvePayout: (id: string) =>
    http.post<ReferralPayoutRead>(`/referrals/payouts/${id}/approve`).then(r => r.data),
  payPayout: (id: string) =>
    http.post<ReferralPayoutRead>(`/referrals/payouts/${id}/pay`).then(r => r.data),
  rejectPayout: (id: string, reason: string) =>
    http.post<ReferralPayoutRead>(`/referrals/payouts/${id}/reject`, { reason }).then(r => r.data),

  // Phase 5 — admin
  stats: () => http.get<ReferralStats>('/referrals/stats').then(r => r.data),
}
