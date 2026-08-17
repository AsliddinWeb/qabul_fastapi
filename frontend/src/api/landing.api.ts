import { http } from '@/api/http'

export interface LandingContent {
  data: Record<string, any>
}

export const landingApi = {
  get: () => http.get<LandingContent>('/landing/content').then((r) => r.data),
  update: (data: Record<string, any>) =>
    http.put<LandingContent>('/landing/content', { data }).then((r) => r.data),
}
