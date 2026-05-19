/**
 * Staff (operator/admin/director) API surface — for managing applicants,
 * applications, and reviews from non-self perspective.
 */

import { http } from '@/api/http'
import type { ApplicantBase, ApplicantDetailed, ApplicantRead } from '@/api/applicants.api'
import type { AdmissionType, ApplicationDetailed, ApplicationStatus } from '@/api/applications.api'

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface OperatorApplicantCreate extends ApplicantBase {
  phone: string
}

export interface ApplicantListFilters {
  status?: string
  region_id?: string
  registered_by_id?: string
  search?: string
  page?: number
  size?: number
}

export interface ApplicationListFilters {
  status?: ApplicationStatus
  admission_type?: AdmissionType
  program_id?: string
  branch_id?: string
  applicant_id?: string
  /** Operator who registered the applicant (filter for admin/superadmin). */
  registered_by_id?: string
  /** 'lead' = converted from a lead; 'direct' = created without lead. */
  source?: 'lead' | 'direct'
  consulting_agency_id?: string
  education_level_id?: string
  education_form_id?: string
  page?: number
  size?: number
}

export const staffApi = {
  applicants: {
    list: (filters: ApplicantListFilters = {}) =>
      http
        .get<PageResponse<ApplicantRead>>('/applicants', { params: filters })
        .then((r) => r.data),

    get: (id: string) =>
      http.get<ApplicantDetailed>(`/applicants/${id}`).then((r) => r.data),

    operatorCreate: (payload: OperatorApplicantCreate) =>
      http.post<ApplicantRead>('/applicants', payload).then((r) => r.data),

    update: (id: string, payload: Partial<ApplicantBase>) =>
      http.patch<ApplicantRead>(`/applicants/${id}`, payload).then((r) => r.data),
  },

  applications: {
    list: (filters: ApplicationListFilters = {}) =>
      http
        .get<PageResponse<ApplicationDetailed>>('/applications', { params: filters })
        .then((r) => r.data),

    get: (id: string) =>
      http.get<ApplicationDetailed>(`/applications/${id}`).then((r) => r.data),

    review: (
      id: string,
      payload: { approved: boolean; rejection_reason?: string; notes?: string },
    ) =>
      http.post<ApplicationDetailed>(`/applications/${id}/review`, payload).then((r) => r.data),

    startReview: (id: string) =>
      http.post<ApplicationDetailed>(`/applications/${id}/start-review`).then((r) => r.data),
  },
}
