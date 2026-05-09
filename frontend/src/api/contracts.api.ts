import { http } from '@/api/http'

export type ContractType = 'two_party' | 'three_party'
export type ContractStatus = 'draft' | 'signed' | 'cancelled' | 'completed'
export type PartyRole = 'university' | 'student' | 'sponsor' | 'parent'
export type Language = 'uz' | 'ru' | 'en'

export interface ContractTemplateRead {
  id: string
  name: string
  body_two_party: string | null
  body_three_party: string | null
  version: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ContractTemplatePayload {
  name: string
  body_two_party?: string | null
  body_three_party?: string | null
  is_active?: boolean
}

export interface AdditionalParty {
  party_role: 'sponsor' | 'parent'
  full_name: string
  pinfl?: string | null
  passport_series?: string | null
  passport_number?: string | null
  phone?: string | null
  relationship?: string | null
  address?: string | null
}

export interface ContractCreatePayload {
  application_id: string
  template_id: string
  type: ContractType
  total_amount?: string | number | null
  currency?: string
  additional_party?: AdditionalParty | null
}

export interface ContractParty {
  id: string
  contract_id: string
  party_role: PartyRole
  full_name: string
  pinfl?: string | null
  passport_series?: string | null
  passport_number?: string | null
  phone?: string | null
  relationship?: string | null
  address?: string | null
}

export interface ContractDetailed {
  id: string
  contract_number: string
  application_id: string
  template_id: string
  type: ContractType
  total_amount: string
  paid_amount: string
  currency: string
  status: ContractStatus
  signed_at: string | null
  pdf_file_id: string | null
  parties: ContractParty[]
  created_at: string
  updated_at: string
}

export interface ContractSettings {
  id: string
  default_contract_type: ContractType
  auto_generate_pdf: boolean
  pdf_page_size: string
  company_name: string
  company_address: string | null
  company_inn: string | null
  director_name: string | null
  director_title: string
  created_at: string
  updated_at: string
}

export interface ContractSettingsUpdatePayload {
  default_contract_type?: ContractType
  auto_generate_pdf?: boolean
  pdf_page_size?: string
  company_name?: string
  company_address?: string | null
  company_inn?: string | null
  director_name?: string | null
  director_title?: string
}

export const contractsApi = {
  templates: () =>
    http.get<ContractTemplateRead[]>('/contracts/templates').then((r) => r.data),

  // Singleton — university identity used in generated contracts/PDFs
  getSettings: () =>
    http.get<ContractSettings>('/contracts/settings').then((r) => r.data),
  updateSettings: (payload: ContractSettingsUpdatePayload) =>
    http.patch<ContractSettings>('/contracts/settings', payload).then((r) => r.data),

  template: (id: string) =>
    http.get<ContractTemplateRead>(`/contracts/templates/${id}`).then((r) => r.data),

  activeTemplate: () =>
    http.get<ContractTemplateRead | null>('/contracts/templates/active').then((r) => r.data),

  createTemplate: (payload: ContractTemplatePayload) =>
    http.post<ContractTemplateRead>('/contracts/templates', payload).then((r) => r.data),

  updateTemplate: (id: string, payload: Partial<ContractTemplatePayload>) =>
    http.patch<ContractTemplateRead>(`/contracts/templates/${id}`, payload).then((r) => r.data),

  activateTemplate: (id: string) =>
    http.post<ContractTemplateRead>(`/contracts/templates/${id}/activate`).then((r) => r.data),

  deleteTemplate: (id: string) =>
    http.delete(`/contracts/templates/${id}`).then((r) => r.data),

  create: (payload: ContractCreatePayload) =>
    http.post<ContractDetailed>('/contracts', payload).then((r) => r.data),

  get: (id: string) =>
    http.get<ContractDetailed>(`/contracts/${id}`).then((r) => r.data),

  // Applicant self-service: own contracts (read-only)
  myList: () =>
    http.get<ContractDetailed[]>('/contracts/me').then((r) => r.data),

  sign: (id: string, notes?: string) =>
    http.post<ContractDetailed>(`/contracts/${id}/sign`, { notes }).then((r) => r.data),

  cancel: (id: string) =>
    http.post<ContractDetailed>(`/contracts/${id}/cancel`).then((r) => r.data),

  pdfUrl: (id: string) => `/api/v1/contracts/${id}/pdf`,

  openPdf: async (id: string) => {
    const res = await http.get(`/contracts/${id}/pdf`, { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)

    // Pull the server's preferred filename out of Content-Disposition so
    // that "Save As..." in the new tab uses e.g. "ABDUJABBOROV-ASLIDDIN.pdf"
    // instead of the contract UUID.
    const cd = (res.headers as any)['content-disposition'] as string | undefined
    let filename = `contract-${id}.pdf`
    if (cd) {
      const star = /filename\*\s*=\s*[^']*''([^;]+)/i.exec(cd)
      const plain = /filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;]+)/i.exec(cd)
      if (star?.[1]) {
        try { filename = decodeURIComponent(star[1]) } catch { /* keep default */ }
      } else if (plain) {
        filename = (plain[1] || plain[2] || '').trim()
      }
    }

    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.target = '_blank'
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  },
}
