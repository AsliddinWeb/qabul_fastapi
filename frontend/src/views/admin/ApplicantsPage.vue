<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { Plus, Users as UsersIcon, Pencil, Trash2, Search, Phone, Download } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi } from '@/api/admin.api'
import { downloadCsv } from '@/api/http'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

interface Applicant {
  id: string
  user_id: string
  last_name: string
  first_name: string
  other_name?: string | null
  passport_series?: string | null
  pinfl?: string | null
  birth_date: string
  gender: 'male' | 'female'
  additional_phone?: string | null
  created_at: string
}

const router = useRouter()
const route = useRoute()
const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')
const toast = useToast()
const { ask } = useConfirm()

const items = ref<Applicant[]>([])
const total = ref(0)
const loading = ref(false)
const filters = reactive({ search: '', page: 1, size: 20 })

async function load() {
  loading.value = true
  try {
    const res = await adminApi.applicants.list({
      search: filters.search || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items as Applicant[]
    total.value = res.total
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(() => filters.search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { filters.page = 1; load() }, 300)
})
watch(() => filters.page, load)
onMounted(load)

async function remove(a: Applicant) {
  const ok = await ask({
    title: "Abituriyentni o'chirish",
    message: `${a.last_name} ${a.first_name} o'chirilsinmi? Diplom va arizalari ham o'chiriladi.`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.applicants.delete(a.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi (arizalar bog'langan)")
  }
}

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    await downloadCsv('/applicants/export.csv', { search: filters.search || undefined })
    toast.success("CSV yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}

// Avatar — restrained 2-stop palette (matches detail page)
const AVATAR_COLORS = [
  'from-slate-600 to-slate-800',
  'from-indigo-500 to-indigo-700',
  'from-violet-500 to-violet-700',
  'from-teal-500 to-teal-700',
  'from-amber-500 to-amber-700',
]
function avatarColor(s: string): string {
  const h = s.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}
function initials(a: Applicant): string {
  return ((a.last_name?.[0] || '') + (a.first_name?.[0] || '')).toUpperCase() || '—'
}
function age(birth: string): number {
  const d = new Date(birth)
  const diff = Date.now() - d.getTime()
  return Math.abs(new Date(diff).getUTCFullYear() - 1970)
}
</script>

<template>
  <div>
    <PageHeader
      title="Abituriyentlar"
      :subtitle="`Tizimda ro'yxatga olingan abituriyentlar · Jami ${total}`"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'Qabul jarayoni' }]"
    >
      <button class="btn-outline" :disabled="exporting" @click="exportCsv">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'CSV' }}
      </button>
      <RouterLink :to="`${panelPrefix}/applicants/new`" class="btn-primary">
        <Plus class="w-4 h-4" /> Qo'lda kiritish
      </RouterLink>
    </PageHeader>

    <div class="filter-bar">
      <div class="flex-1 min-w-[260px]">
        <label class="field-label">Qidirish</label>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input v-model="filters.search" class="input pl-10"
                 placeholder="F.I.Sh., pasport (AA1234567), PINFL..." />
        </div>
      </div>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Abituriyent</th>
            <th class="w-44">Pasport / PINFL</th>
            <th class="w-40">Tug'ilgan sana</th>
            <th class="w-40">Telefon</th>
            <th class="w-32 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="i in 6" :key="`sk-row-${i}`" class="border-b border-slate-100 dark:border-slate-800/60">
              <td v-for="c in 5" :key="`sk-${i}-${c}`" class="px-5 py-4">
                <div class="skeleton h-3 rounded" :class="c === 1 ? 'w-3/4' : 'w-1/2'" />
              </td>
            </tr>
          </template>
          <tr v-else-if="!items.length">
            <td colspan="5" class="p-0">
              <EmptyState :icon="UsersIcon" title="Abituriyentlar topilmadi"
                          subtitle="Qidiruv natijasi bo'sh — boshqa kalit so'z bilan qaytadan urinib ko'ring" />
            </td>
          </tr>
          <tr v-for="a in items" :key="a.id" class="cursor-pointer"
              @click="router.push(`${panelPrefix}/applicants/${a.id}`)">
            <td>
              <div class="flex items-center gap-3">
                <div class="avatar bg-gradient-to-br text-white" :class="avatarColor(a.id)">
                  {{ initials(a) }}
                </div>
                <div class="min-w-0">
                  <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                    {{ a.last_name }} {{ a.first_name }}
                  </div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 truncate">
                    {{ a.other_name || '—' }}
                  </div>
                </div>
              </div>
            </td>
            <td class="text-xs text-slate-600 dark:text-slate-400 font-mono">
              <div>{{ a.passport_series || '—' }}</div>
              <div class="text-slate-500">{{ a.pinfl || '—' }}</div>
            </td>
            <td>
              <div class="text-sm text-slate-700 dark:text-slate-300">{{ a.birth_date }}</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">{{ age(a.birth_date) }} yosh</div>
            </td>
            <td>
              <div v-if="a.additional_phone" class="inline-flex items-center gap-1.5 text-xs font-mono text-slate-600 dark:text-slate-400">
                <Phone class="w-3 h-3" /> {{ a.additional_phone }}
              </div>
              <span v-else class="text-xs text-slate-400">—</span>
            </td>
            <td class="text-right" @click.stop>
              <div class="inline-flex items-center gap-1.5">
                <RouterLink :to="`${panelPrefix}/applicants/${a.id}`" class="btn-outline btn-sm">
                  <Pencil class="w-3.5 h-3.5" /> Ko'rish
                </RouterLink>
                <button v-if="!isOperatorPanel" class="icon-btn-danger" title="O'chirish" @click="remove(a)">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="items.length" class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">
          Sahifa <strong class="text-slate-700 dark:text-slate-300">{{ filters.page }}</strong> / {{ lastPage() }}
        </div>
        <div class="flex gap-2">
          <button class="btn-outline btn-sm" :disabled="filters.page <= 1" @click="filters.page--">‹ Oldingi</button>
          <button class="btn-outline btn-sm" :disabled="filters.page >= lastPage()" @click="filters.page++">Keyingi ›</button>
        </div>
      </div>
    </div>
  </div>
</template>
