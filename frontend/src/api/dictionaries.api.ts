import { http } from '@/api/http'

export interface DictionaryItem {
  id: string
  type_id: string
  parent_id?: string | null
  code?: string | null
  name_uz: string
  name_ru?: string | null
  name_en?: string | null
  sort_order: number
  is_active: boolean
}

export const dictionariesApi = {
  items: (type_code: string, parent_id?: string) =>
    http
      .get<DictionaryItem[]>('/dictionaries/items', { params: { type_code, parent_id } })
      .then((r) => r.data),
}
