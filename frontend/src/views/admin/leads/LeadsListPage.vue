<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Plus, Users as UsersIcon, Search, X as XIcon, LayoutGrid, Filter as FilterIcon,
  Phone, MoreVertical, Trash2, Eye, Download, Send, ArrowRight,
} from 'lucide-vue-next'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { AxiosError } from 'axios'
import { leadsApi, type Lead, type LeadPipeline, type LeadStage, type LeadSource, type LeadStatus, type LeadStats } from '@/api/leads.api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import EmptyState from '@/components/ui/EmptyState.vue'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import { formatPhone } from '@/utils/validators'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const toast = useToast()
const { ask } = useConfirm()

// Operator panel uses myOnly meta — auto-filter by current user
const myOnly = computed(() => !!route.meta?.myOnly)
const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')

const items = ref<Lead[]>([])
const total = ref(0)
const stats = ref<LeadStats | null>(null)
const loading = ref(false)

const pipelines = ref<LeadPipeline[]>([])
const stages = ref<LeadStage[]>([])
const sources = ref<LeadSource[]>([])

const filters = reactive({
  pipeline_id: '' as string,
  stage_id: '' as string,
  status: '' as LeadStatus | '',
  source_id: '' as string,
  search: '' as string,
  page: 1,
  size: 50,
})

const STATUS_OPTIONS = [
  { id: 'open', label: 'Faol' },
  { id: 'won',  label: 'Yutilgan' },
  { id: 'lost', label: "Yo'qotilgan" },
]

const pipelineOptions = computed(() => pipelines.value.map(p => ({ id: p.id, label: p.name })))
const stageOptions = computed(() =>
  filters.pipeline_id ? stages.value.filter(s => s.pipeline_id === filters.pipeline_id).map(s => ({ id: s.id, label: s.name })) : [],
)
const sourceOptions = computed(() => sources.value.map(s => ({ id: s.id, label: s.name })))

async function loadCatalogs() {
  const [pp, src] = await Promise.all([
    leadsApi.pipelines.list().catch(() => []),
    leadsApi.sources.list().catch(() => []),
  ])
  pipelines.value = pp
  sources.value = src
  if (!filters.pipeline_id) {
    const def = pp.find(p => p.is_default) || pp[0]
    if (def) filters.pipeline_id = def.id
  }
  if (filters.pipeline_id) {
    stages.value = await leadsApi.stages.list(filters.pipeline_id).catch(() => [])
  }
}

async function loadStats() {
  try { stats.value = await leadsApi.stats(filters.pipeline_id || undefined) } catch { /* ignore */ }
}

async function load() {
  loading.value = true
  try {
    const res = await leadsApi.list({
      pipeline_id: filters.pipeline_id || undefined,
      stage_id: filters.stage_id || undefined,
      status: filters.status || undefined,
      source_id: filters.source_id || undefined,
      assigned_to_id: myOnly.value ? (auth.user?.id || undefined) : undefined,
      search: filters.search || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadCatalogs()
  await Promise.all([load(), loadStats()])
})

let searchT: ReturnType<typeof setTimeout> | null = null
watch(() => filters.search, () => {
  if (searchT) clearTimeout(searchT)
  searchT = setTimeout(() => { filters.page = 1; load() }, 300)
})
watch(() => filters.pipeline_id, async (v) => {
  filters.stage_id = ''
  stages.value = v ? await leadsApi.stages.list(v).catch(() => []) : []
  filters.page = 1
  await Promise.all([load(), loadStats()])
})
watch(() => [filters.stage_id, filters.status, filters.source_id], () => { filters.page = 1; load() })
watch(() => filters.page, load)

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

function statusPill(s: LeadStatus): string {
  return s === 'open'
    ? 'bg-brand-50 text-brand-700 ring-brand-200 dark:bg-brand-500/15 dark:text-brand-300 dark:ring-brand-700/40'
    : s === 'won'
      ? 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-700/40'
      : 'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:ring-rose-700/40'
}
function statusLabel(s: LeadStatus): string {
  return s === 'open' ? 'Faol' : s === 'won' ? 'Yutilgan' : "Yo'qotilgan"
}
function statusDot(s: LeadStatus): string {
  return s === 'open' ? 'bg-brand-500' : s === 'won' ? 'bg-emerald-500' : 'bg-rose-500'
}

function relTime(iso: string): string {
  const d = new Date(iso); const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'Hozir'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} daq oldin`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat oldin`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} kun oldin`
  return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short' })
}

const activeFilterCount = computed(() => {
  let n = 0
  if (filters.stage_id) n++
  if (filters.status) n++
  if (filters.source_id) n++
  return n
})

function clearFilters() {
  filters.stage_id = ''
  filters.status = ''
  filters.source_id = ''
  filters.search = ''
}

function setStatusFilter(s: 'open' | 'won' | 'lost') {
  filters.status = (filters.status === s ? '' : s) as any
}

const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    await leadsApi.exportCsv({
      pipeline_id: filters.pipeline_id || undefined,
      stage_id: filters.stage_id || undefined,
      status: filters.status || undefined,
      source_id: filters.source_id || undefined,
      search: filters.search || undefined,
    })
    toast.success("CSV yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}

async function deleteLead(l: Lead) {
  const ok = await ask({
    title: "Lead'ni o'chirish",
    message: `${l.full_name} (${l.phone}) o'chirilsinmi?`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await leadsApi.delete(l.id)
    toast.success("O'chirildi")
    await Promise.all([load(), loadStats()])
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

function avatarInitials(s: string): string {
  const parts = (s || '').split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '—'
}

// === Color helpers for visual badges ===

// Per-source palette by source code (matches our 7 default sources).
const SOURCE_TONE: Record<string, string> = {
  web_form:  'bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-700/40',
  telegram:  'bg-cyan-50 text-cyan-700 ring-cyan-200 dark:bg-cyan-500/10 dark:text-cyan-300 dark:ring-cyan-700/40',
  instagram: 'bg-pink-50 text-pink-700 ring-pink-200 dark:bg-pink-500/10 dark:text-pink-300 dark:ring-pink-700/40',
  call:      'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-700/40',
  walk_in:   'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-700/40',
  referral:  'bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-500/10 dark:text-violet-300 dark:ring-violet-700/40',
  agent:     'bg-indigo-50 text-indigo-700 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-700/40',
}
function sourceTone(code: string | null): string {
  return code && SOURCE_TONE[code]
    ? SOURCE_TONE[code]
    : 'bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700'
}

// Hex → rgba for ring/bg derivation.
function hexToRgba(hex: string | null, alpha = 0.12): string {
  if (!hex) return `rgba(100, 116, 139, ${alpha})`
  const m = hex.replace('#', '').match(/^([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i)
  if (!m) return `rgba(100, 116, 139, ${alpha})`
  const r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// Operator avatar gradient palette — deterministic by name hash.
const OP_AVATARS = [
  'from-violet-500 to-violet-700',
  'from-emerald-500 to-teal-600',
  'from-rose-500 to-pink-600',
  'from-sky-500 to-indigo-600',
  'from-amber-500 to-orange-600',
  'from-cyan-500 to-blue-600',
]
function opAvatarTone(name: string | null): string {
  const s = name || ''
  const h = s.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return OP_AVATARS[h % OP_AVATARS.length]
}
</script>

<template>
  <div>
    <PageHeader
      :title="myOnly ? `Mening lead'larim` : 'Leadlar'"
      :subtitle="myOnly ? `Sizga biriktirilgan lead'lar — varonkangizni boshqaring` : 'Potensial abituriyentlar — varonkani boshqarish'"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'CRM' }]"
    >
      <button class="btn-outline" :disabled="exporting" @click="exportCsv">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'CSV' }}
      </button>
      <RouterLink :to="`${panelPrefix}/leads/board`" class="btn-outline">
        <LayoutGrid class="w-4 h-4" /> Kanban
      </RouterLink>
      <RouterLink :to="`${panelPrefix}/leads/new`" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi lead
      </RouterLink>
    </PageHeader>

    <!-- Stat tiles (clickable status filter) -->
    <div v-if="stats" class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
      <button type="button"
              class="text-left rounded-2xl p-4 border bg-white dark:bg-slate-900 transition-all hover:shadow-md hover:-translate-y-0.5"
              :class="!filters.status ? 'border-brand-300 ring-2 ring-brand-200/60 dark:border-brand-600 dark:ring-brand-700/30' : 'border-slate-200/70 dark:border-slate-800'"
              @click="filters.status = '' as any">
        <div class="flex items-center justify-between">
          <span class="grid place-items-center w-9 h-9 rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <UsersIcon class="w-4 h-4" />
          </span>
        </div>
        <div class="mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 tabular-nums">{{ stats.total }}</div>
        <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mt-0.5 font-semibold">Jami leadlar</div>
      </button>

      <button type="button"
              class="text-left rounded-2xl p-4 border bg-white dark:bg-slate-900 transition-all hover:shadow-md hover:-translate-y-0.5"
              :class="filters.status === 'open' ? 'border-brand-400 ring-2 ring-brand-300/60' : 'border-slate-200/70 dark:border-slate-800'"
              @click="setStatusFilter('open')">
        <div class="flex items-center justify-between">
          <span class="grid place-items-center w-9 h-9 rounded-lg bg-brand-500 text-white shadow-sm">
            <Send class="w-4 h-4" />
          </span>
          <span class="w-2 h-2 rounded-full bg-brand-500 animate-pulse"></span>
        </div>
        <div class="mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 tabular-nums">{{ stats.open }}</div>
        <div class="text-[11px] uppercase tracking-wider text-brand-700 dark:text-brand-300 mt-0.5 font-semibold">Faol</div>
      </button>

      <button type="button"
              class="text-left rounded-2xl p-4 border bg-white dark:bg-slate-900 transition-all hover:shadow-md hover:-translate-y-0.5"
              :class="filters.status === 'won' ? 'border-emerald-400 ring-2 ring-emerald-300/60' : 'border-slate-200/70 dark:border-slate-800'"
              @click="setStatusFilter('won')">
        <div class="flex items-center justify-between">
          <span class="grid place-items-center w-9 h-9 rounded-lg bg-emerald-500 text-white shadow-sm">
            <ArrowRight class="w-4 h-4" />
          </span>
        </div>
        <div class="mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 tabular-nums">{{ stats.won }}</div>
        <div class="text-[11px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300 mt-0.5 font-semibold">Yutilgan ({{ stats.conversion_rate }}%)</div>
      </button>

      <button type="button"
              class="text-left rounded-2xl p-4 border bg-white dark:bg-slate-900 transition-all hover:shadow-md hover:-translate-y-0.5"
              :class="filters.status === 'lost' ? 'border-rose-400 ring-2 ring-rose-300/60' : 'border-slate-200/70 dark:border-slate-800'"
              @click="setStatusFilter('lost')">
        <div class="flex items-center justify-between">
          <span class="grid place-items-center w-9 h-9 rounded-lg bg-rose-500 text-white shadow-sm">
            <XIcon class="w-4 h-4" />
          </span>
        </div>
        <div class="mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 tabular-nums">{{ stats.lost }}</div>
        <div class="text-[11px] uppercase tracking-wider text-rose-700 dark:text-rose-300 mt-0.5 font-semibold">Yo'qotilgan</div>
      </button>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-4 flex flex-col gap-3">
      <div class="w-full flex items-center justify-between">
        <div class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 inline-flex items-center gap-2">
          <FilterIcon class="w-3.5 h-3.5" /> Filtrlar
          <span v-if="activeFilterCount" class="px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px]">
            {{ activeFilterCount }}
          </span>
        </div>
        <button v-if="activeFilterCount || filters.search"
                class="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1"
                @click="clearFilters">
          <XIcon class="w-3 h-3" /> Tozalash
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div class="lg:col-span-2">
          <label class="field-label">Qidirish</label>
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input v-model="filters.search" class="input pl-10" placeholder="F.I.Sh. yoki telefon" />
          </div>
        </div>
        <div>
          <label class="field-label">Varonka</label>
          <SearchSelect v-model="filters.pipeline_id" :options="pipelineOptions" placeholder="— tanlang —" />
        </div>
        <div>
          <label class="field-label">Bosqich</label>
          <SearchSelect v-model="filters.stage_id" :options="stageOptions" placeholder="— hammasi —" allow-clear :disabled="!filters.pipeline_id" />
        </div>
        <div>
          <label class="field-label">Manba</label>
          <SearchSelect v-model="filters.source_id" :options="sourceOptions" placeholder="— hammasi —" allow-clear />
        </div>
      </div>
    </div>

    <!-- Loading / empty -->
    <Skeleton v-if="loading" type="table" />
    <div v-else-if="!items.length" class="card p-6">
      <EmptyState :icon="UsersIcon" title="Leadlar topilmadi" subtitle="Filtrlarni tozalang yoki yangi lead qo'shing">
        <RouterLink :to="`${panelPrefix}/leads/new`" class="btn-primary mt-4 inline-flex">
          <Plus class="w-4 h-4" /> Yangi lead
        </RouterLink>
      </EmptyState>
    </div>

    <!-- Table -->
    <div v-else class="card">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 dark:border-slate-800
                       text-[10px] uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
              <th class="text-left font-semibold px-5 py-3.5">Lead</th>
              <th class="text-left font-semibold px-4 py-3.5 w-44">Bosqich</th>
              <th class="text-left font-semibold px-4 py-3.5 w-32">Manba</th>
              <th class="text-left font-semibold px-4 py-3.5">Yo'nalish</th>
              <th class="text-left font-semibold px-4 py-3.5 w-36">Operator</th>
              <th class="text-left font-semibold px-4 py-3.5 w-28">Holati</th>
              <th class="text-left font-semibold px-4 py-3.5 w-28">Vaqt</th>
              <th class="text-right font-semibold px-5 py-3.5 w-28">Amal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in items" :key="l.id"
                class="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors cursor-pointer group"
                @click="router.push(`${panelPrefix}/leads/${l.id}`)">
              <td class="px-5 py-4">
                <div class="flex items-center gap-3.5">
                  <div class="grid place-items-center w-11 h-11 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300 text-sm font-bold shrink-0 ring-2 ring-brand-100/50 dark:ring-brand-700/30">
                    {{ avatarInitials(l.full_name) }}
                  </div>
                  <div class="min-w-0">
                    <div class="font-semibold text-slate-900 dark:text-slate-100 truncate group-hover:text-brand-700 dark:group-hover:text-brand-300 transition-colors">{{ l.full_name }}</div>
                    <div class="text-[11px] text-slate-500 dark:text-slate-400 inline-flex items-center gap-1.5 font-mono">
                      <Phone class="w-3 h-3" /> {{ formatPhone(l.phone) }}
                    </div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-4">
                <span v-if="l.stage_name"
                      class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ring-1"
                      :style="{
                        backgroundColor: hexToRgba(l.stage_color, 0.12),
                        color: l.stage_color || '#475569',
                        boxShadow: `inset 0 0 0 1px ${hexToRgba(l.stage_color, 0.3)}`,
                      }">
                  <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: l.stage_color || '#94a3b8' }"></span>
                  {{ l.stage_name }}
                </span>
                <span v-else class="text-xs text-slate-400">—</span>
              </td>
              <td class="px-4 py-4">
                <span v-if="l.source_name"
                      class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold ring-1"
                      :class="sourceTone(l.source_code)">
                  {{ l.source_name }}
                </span>
                <span v-else class="text-xs text-slate-400">—</span>
              </td>
              <td class="px-4 py-4 min-w-0">
                <div class="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{{ l.program_name || '—' }}</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">{{ l.branch_name || '—' }}</div>
              </td>
              <td class="px-4 py-4">
                <div v-if="l.assigned_to_name" class="flex items-center gap-2 min-w-0">
                  <span class="grid place-items-center w-7 h-7 rounded-full bg-gradient-to-br text-white text-[10px] font-bold shrink-0"
                        :class="opAvatarTone(l.assigned_to_name)">
                    {{ avatarInitials(l.assigned_to_name) }}
                  </span>
                  <span class="text-xs text-slate-700 dark:text-slate-300 truncate">{{ l.assigned_to_name }}</span>
                </div>
                <span v-else class="inline-flex items-center gap-1.5 text-xs text-slate-400">
                  <span class="w-7 h-7 rounded-full border-2 border-dashed border-slate-200 dark:border-slate-700"></span>
                  Biriktirilmagan
                </span>
              </td>
              <td class="px-4 py-4">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ring-1"
                      :class="statusPill(l.status)">
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusDot(l.status)"></span>
                  {{ statusLabel(l.status) }}
                </span>
              </td>
              <td class="px-4 py-4 text-[11px] text-slate-500 dark:text-slate-400">{{ relTime(l.created_at) }}</td>
              <td class="px-5 py-4" @click.stop>
                <div class="flex items-center justify-end gap-1.5">
                  <RouterLink :to="`${panelPrefix}/leads/${l.id}`" class="btn-outline btn-sm">
                    <Eye class="w-3.5 h-3.5" /> Ko'rish
                  </RouterLink>
                  <Dropdown align="right">
                    <template #trigger>
                      <button class="icon-btn" title="Ko'proq">
                        <MoreVertical class="w-4 h-4" />
                      </button>
                    </template>
                    <button class="menu-item !text-rose-600 dark:!text-rose-400 hover:!bg-rose-50 dark:hover:!bg-rose-900/30" @click="deleteLead(l)">
                      <Trash2 class="w-4 h-4" /> O'chirish
                    </button>
                  </Dropdown>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">
          Sahifa <strong class="text-slate-700 dark:text-slate-300">{{ filters.page }}</strong> / {{ lastPage() }}
          <span class="mx-1">·</span>
          Jami <strong class="text-slate-700 dark:text-slate-300">{{ total }}</strong>
        </div>
        <div class="flex gap-2">
          <button class="btn-outline btn-sm" :disabled="filters.page <= 1" @click="filters.page--">‹ Oldingi</button>
          <button class="btn-outline btn-sm" :disabled="filters.page >= lastPage()" @click="filters.page++">Keyingi ›</button>
        </div>
      </div>
    </div>
  </div>
</template>
