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

export const referralsApi = {
  // Current user
  myCode: () => http.get<ReferralCode>('/referrals/me/code').then(r => r.data),
  mine: (status?: ReferralStatus) =>
    http.get<ReferralRead[]>('/referrals/me', {
      params: status ? { status_filter: status } : undefined,
    }).then(r => r.data),

  // Staff
  list: (params: { status_filter?: ReferralStatus; referrer_user_id?: string } = {}) =>
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
}
