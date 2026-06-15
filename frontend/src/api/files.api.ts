/**
 * Files helper used by FilePreview / FileUpload.
 *
 * Two URLs come back from /files/{id}/meta:
 *   - meta.url is the static media path. Public for things like
 *     program images, but for staff-only uploads (diplom skans,
 *     payment receipts, contract PDFs) the FastAPI download endpoint
 *     is the actually-authorised path. Use authedDownloadUrl() to
 *     build the auth-via-?token=… variant so an <img> or <iframe>
 *     can load it from a fresh browser tab without setting headers.
 *   - meta.mime_type drives how the preview renders (image vs PDF
 *     vs generic file icon).
 */
import { http } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

export interface FileMeta {
  id: string
  original_name: string
  mime_type: string
  size_bytes: number
  /** Static media URL; only loadable for public-marked files. */
  url: string
}

export const filesApi = {
  meta: (id: string) =>
    http.get<FileMeta>(`/files/${id}/meta`).then(r => r.data),
}

/**
 * Auth-via-querystring download URL — what <img src> and <iframe src>
 * actually want. The /files/{id}/download endpoint accepts the access
 * token as a ?token= param specifically so it can be used outside an
 * axios call (where we'd attach the Bearer header).
 */
export function authedDownloadUrl(id: string): string | null {
  const auth = useAuthStore()
  if (!auth.accessToken) return null
  const base = (http.defaults.baseURL || '').replace(/\/$/, '')
  return `${base}/files/${id}/download?token=${encodeURIComponent(auth.accessToken)}`
}
