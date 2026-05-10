import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'
import { useAuthStore } from '@/stores/auth'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const http: AxiosInstance = axios.create({
  baseURL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

// Bare client without interceptors — used for the refresh call itself.
const bareHttp = axios.create({ baseURL, timeout: 20000 })

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

// In-flight refresh promise so concurrent 401s share one refresh.
let refreshInFlight: Promise<string | null> | null = null

async function performRefresh(refreshToken: string): Promise<string | null> {
  try {
    const { data } = await bareHttp.post<{
      access_token: string
      refresh_token: string
      expires_in: number
    }>('/auth/refresh', { refresh_token: refreshToken })

    const auth = useAuthStore()
    if (auth.user) {
      auth.setSession(data.access_token, data.refresh_token, auth.user)
    } else {
      auth.accessToken = data.access_token
      auth.refreshToken = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
    }
    return data.access_token
  } catch {
    return null
  }
}

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  return config
})

/**
 * Fetch a CSV (or any file) from the API and trigger a browser download.
 * Reads the server's Content-Disposition for the filename when available.
 */
export async function downloadCsv(
  path: string,
  params: Record<string, any> = {},
  fallbackName?: string,
): Promise<void> {
  const res = await http.get(path, { params, responseType: 'blob' })
  const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const cd = (res.headers as any)['content-disposition'] as string | undefined
  const m = cd?.match(/filename="?([^";]+)"?/i)
  a.href = url
  a.download = m?.[1] || fallbackName || `export-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')}.csv`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 30_000)
}

http.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined
    const auth = useAuthStore()

    // Only attempt refresh on 401, once per request, when we have a refresh token
    // and we're not already trying to refresh.
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      auth.refreshToken &&
      !original.url?.endsWith('/auth/refresh')
    ) {
      original._retry = true

      refreshInFlight ??= performRefresh(auth.refreshToken).finally(() => {
        refreshInFlight = null
      })

      const newToken = await refreshInFlight
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return http.request(original as AxiosRequestConfig)
      }

      auth.logout()
    }

    return Promise.reject(error)
  },
)
