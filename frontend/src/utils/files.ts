/**
 * Build a download URL for a stored file that works in a regular <a target="_blank">.
 *
 * The /files/{id}/download endpoint accepts JWT either as `Authorization: Bearer ...`
 * (used by axios calls) or as `?token=<jwt>` (so a plain anchor in a new tab works).
 * We attach the current access token so admins can click "view file" links.
 */
export function fileUrl(fileId: string | null | undefined): string | null {
  if (!fileId) return null
  const token = (typeof localStorage !== 'undefined' ? localStorage.getItem('access_token') : null) || ''
  const qs = token ? `?token=${encodeURIComponent(token)}` : ''
  return `/api/v1/files/${fileId}/download${qs}`
}
