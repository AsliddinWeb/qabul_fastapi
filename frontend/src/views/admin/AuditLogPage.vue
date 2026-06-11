<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useRouter } from 'vue-router'
import {
  Shield, FilePlus2, FileEdit, Trash2, Activity, ArrowRight,
  X as XIcon, Search, Clock, User as UserIcon,
} from 'lucide-vue-next'
import Skeleton from '@/components/ui/Skeleton.vue'
import Pagination from '@/components/ui/Pagination.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { http } from '@/api/http'
import EmptyState from '@/components/ui/EmptyState.vue'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import { AUDIT_ACTIONS, AUDIT_ENTITY_TYPES, ROLE, auditCategory, tr } from '@/utils/labels'

interface AuditLog {
  id: string
  user_id: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  changes: any
  ip_address: string | null
  user_agent: string | null
  created_at: string
  user_full_name: string | null
  user_phone: string | null
  user_role: string | null
}

interface PageResponse<T> { items: T[]; total: number; page: number; size: number }

const router = useRouter()
const items = ref<AuditLog[]>([])
const total = ref(0)
const loading = ref(false)
const { filters, clear: clearAllFilters, hasActiveFilters } = useUrlFilters({
  action: '',
  entity_type: '',
  date_from: '',
  date_to: '',
  search: '',
  page: 1,
  size: 50,
})

const ACTION_OPTIONS = Object.entries(AUDIT_ACTIONS).map(([id, label]) => ({ id, label, sub: id }))
const ENTITY_OPTIONS = Object.entries(AUDIT_ENTITY_TYPES).map(([id, label]) => ({ id, label, sub: id }))

async function load() {
  loading.value = true
  try {
    const res = await http.get<PageResponse<AuditLog>>('/audit', {
      params: {
        action: filters.action || undefined,
        entity_type: filters.entity_type || undefined,
        date_from: filters.date_from ? new Date(filters.date_from).toISOString() : undefined,
        date_to: filters.date_to ? new Date(filters.date_to).toISOString() : undefined,
        page: filters.page,
        size: filters.size,
      },
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  const q = filters.search.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter((l) =>
    (l.user_full_name || '').toLowerCase().includes(q) ||
    (l.user_phone || '').toLowerCase().includes(q) ||
    (l.action || '').toLowerCase().includes(q) ||
    (l.ip_address || '').toLowerCase().includes(q),
  )
})

onMounted(load)
watch(() => filters.action, () => { filters.page = 1; load() })
watch(() => filters.entity_type, () => { filters.page = 1; load() })
watch(() => filters.date_from, () => { filters.page = 1; load() })
watch(() => filters.date_to, () => { filters.page = 1; load() })
watch(() => filters.page, load)

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

function actionLabel(a: string): string {
  return AUDIT_ACTIONS[a] || a
}

function userDisplay(l: AuditLog): string {
  return l.user_full_name || l.user_phone || (l.user_id ? l.user_id.slice(0, 8) + '…' : '—')
}

function userInitials(l: AuditLog): string {
  const n = l.user_full_name
  if (n) {
    const parts = n.split(/\s+/).filter(Boolean)
    return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
  }
  if (l.user_phone) return l.user_phone.slice(-2)
  return '?'
}

const CAT_ICON = { create: FilePlus2, update: FileEdit, delete: Trash2, status: Activity, other: Shield }
const CAT_COLOR: Record<string, string> = {
  create: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  update: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  delete: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
  status: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  other:  'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

function fmtTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function relativeTime(iso: string): string {
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'Hozir'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} daqiqa oldin`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat oldin`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} kun oldin`
  return d.toLocaleDateString('uz-UZ')
}

function clearFilters() {
  clearAllFilters()
}

const activeCount = computed(() => {
  let n = 0
  if (filters.action) n++
  if (filters.entity_type) n++
  if (filters.date_from) n++
  if (filters.date_to) n++
  return n
})
</script>

<template>
  <div>
    <PageHeader
      title="Audit jurnali"
      subtitle="Tizimdagi muhim hodisalar: kim, qachon, nimani, qaysi amal bilan o'zgartirgan"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Sozlamalar' }]"
    />

    <!-- Filters -->
    <div class="card p-4 mb-4 flex flex-col gap-3">
      <div class="w-full flex items-center justify-between">
        <div class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 inline-flex items-center gap-2">
          <Shield class="w-3.5 h-3.5" /> Filtrlar
          <span v-if="activeCount" class="px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px]">
            {{ activeCount }}
          </span>
        </div>
        <button v-if="activeCount || filters.search" type="button"
                class="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1"
                @click="clearFilters">
          <XIcon class="w-3 h-3" /> Tozalash
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3 w-full">
        <div class="lg:col-span-2">
          <label class="field-label">Qidirish (joriy sahifada)</label>
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input v-model="filters.search" class="input pl-10" placeholder="F.I.Sh., telefon, amal, IP..." />
          </div>
        </div>
        <div>
          <label class="field-label">Amal turi</label>
          <SearchSelect v-model="filters.action" :options="ACTION_OPTIONS" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Obyekt</label>
          <SearchSelect v-model="filters.entity_type" :options="ENTITY_OPTIONS" placeholder="— hammasi —" allow-clear />
        </div>
        <div class="grid grid-cols-2 gap-2 sm:col-span-3 lg:col-span-1">
          <div>
            <label class="field-label">Dan</label>
            <input v-model="filters.date_from" type="date" class="input" />
          </div>
          <div>
            <label class="field-label">Gacha</label>
            <input v-model="filters.date_to" type="date" class="input" />
          </div>
        </div>
      </div>
    </div>

    <!-- Loading / empty -->
    <Skeleton v-if="loading" type="table" />

    <div v-else-if="!filtered.length" class="card p-6">
      <EmptyState :icon="Shield" title="Audit yozuvlari yo'q" subtitle="Filtrlarni tozalab ko'ring" />
    </div>

    <!-- Timeline -->
    <div v-else class="card overflow-hidden">
      <ul class="divide-y divide-slate-100 dark:divide-slate-800/60">
        <li v-for="log in filtered" :key="log.id"
            class="px-4 py-3 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors cursor-pointer group"
            @click="router.push(`/admin/audit/${log.id}`)">
          <div class="flex items-start gap-3">
            <!-- Action category icon -->
            <div class="w-9 h-9 rounded-xl grid place-items-center shrink-0"
                 :class="CAT_COLOR[auditCategory(log.action)]">
              <component :is="CAT_ICON[auditCategory(log.action)]" class="w-4 h-4" />
            </div>

            <!-- Body -->
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span class="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                  {{ actionLabel(log.action) }}
                </span>
                <span class="text-xs text-slate-500 dark:text-slate-400">
                  · {{ tr(AUDIT_ENTITY_TYPES, log.entity_type || '') }}
                </span>
                <span v-if="log.entity_id" class="font-mono text-[11px] text-slate-400 dark:text-slate-500">
                  {{ log.entity_id.slice(0, 8) }}…
                </span>
              </div>

              <div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-400">
                <span class="inline-flex items-center gap-1.5">
                  <span class="w-5 h-5 rounded-full grid place-items-center bg-slate-200 dark:bg-slate-700 text-[10px] font-semibold text-slate-600 dark:text-slate-300">
                    {{ userInitials(log) }}
                  </span>
                  <span class="font-medium text-slate-700 dark:text-slate-300">{{ userDisplay(log) }}</span>
                  <span v-if="log.user_role" class="pill ml-1">{{ tr(ROLE, log.user_role) }}</span>
                </span>
                <span class="inline-flex items-center gap-1">
                  <Clock class="w-3 h-3" /> {{ relativeTime(log.created_at) }}
                </span>
                <span v-if="log.ip_address" class="font-mono text-[11px] text-slate-400 dark:text-slate-500">
                  {{ log.ip_address }}
                </span>
              </div>
            </div>

            <ArrowRight class="w-4 h-4 text-slate-300 dark:text-slate-700 group-hover:text-slate-600 dark:group-hover:text-slate-400 mt-2 transition-colors shrink-0" />
          </div>
        </li>
      </ul>

      <Pagination v-model:page="filters.page" :last-page="lastPage()" :total="total" :size="filters.size" />
    </div>
  </div>
</template>
