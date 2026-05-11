import { http } from '@/api/http'

export type Gender = 'male' | 'female'

/** Reflects new backend AbituriyentProfile-shape. */
export interface ApplicantBase {
  last_name: string
  first_name: string
  other_name?: string | null
  birth_date: string
  gender: Gender
  passport_series?: string | null
  pinfl?: string | null
  region_id?: string | null
  district_id?: string | null
  address?: string | null
  nationality?: string
  additional_phone?: string | null
  email?: string | null
  telegram_username?: string | null
  image_id?: string | null
  passport_file_id?: string | null
  // Optional invite code captured from the ?ref=CODE link at sign-in;
  // server records a pending referral row when present.
  referrer_code?: string | null
}

export interface ApplicantRead extends ApplicantBase {
  id: string
  user_id: string
  registered_by_id?: string | null
  created_at: string
  updated_at: string
}

// ---- Diploms (1-kurs / perevod) ----
export interface DiplomPayload {
  user_id: string
  serial_number: string
  education_type_id: string
  institution_type_id: string
  university_name: string
  graduation_year: string
  region_id: string
  district_id: string
  diploma_file_id?: string | null
}

export interface DiplomRead extends DiplomPayload {
  id: string
  created_at: string
  updated_at: string
}

export interface TransferDiplomPayload {
  user_id: string
  country_id: string
  university_name: string
  target_course_id: string
  transcript_file_id?: string | null
}

export interface TransferDiplomRead extends TransferDiplomPayload {
  id: string
  created_at: string
  updated_at: string
}

export interface ApplicantDetailed extends ApplicantRead {
  diplom: DiplomRead | null
  transfer_diplom: TransferDiplomRead | null
}

export const applicantsApi = {
  // Backend returns 200 + null when the current user hasn't created an
  // applicant profile yet (first-login state).
  me: () => http.get<ApplicantDetailed | null>('/applicants/me').then((r) => r.data),

  createMe: (payload: ApplicantBase) =>
    http.post<ApplicantRead>('/applicants/me', payload).then((r) => r.data),

  updateMe: (payload: Partial<ApplicantBase>) =>
    http.patch<ApplicantRead>('/applicants/me', payload).then((r) => r.data),

  upsertDiplom: (payload: DiplomPayload) =>
    http.put<DiplomRead>('/applicants/me/diplom', payload).then((r) => r.data),

  upsertTransferDiplom: (payload: TransferDiplomPayload) =>
    http.put<TransferDiplomRead>('/applicants/me/transfer-diplom', payload).then((r) => r.data),
}
