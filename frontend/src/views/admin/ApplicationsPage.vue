<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import {
  CheckCircle2, XCircle, ClipboardList, Trash2, PlayCircle, Plus, Pencil,
  Search, Clock, Inbox, FileCheck, FileX, Eye, Filter as FilterIcon,
  ArrowUpRight, MoreVertical, X as XIcon, ChevronDown, Check, Download,
} from 'lucide-vue-next'
import { downloadFile } from '@/api/http'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { AxiosError } from 'axios'
import { adminApi } from '@/api/admin.api'
import { consultingApi, type ConsultingAgency } from '@/api/consulting.api'
import { useAuthStore } from '@/stores/auth'
import EmptyState from '@/components/ui/EmptyState.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import { APPLICATION_STATUS, ADMISSION_TYPE, tr } from '@/utils/labels'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useBulkSelect } from '@/composables/useBulkSelect'
import BulkActionBar from '@/components/ui/BulkActionBar.vue'
import Pagination from '@/components/ui/Pagination.vue'

interface Application {
  id: string
  application_number: string
  applicant_id: string
  admission_type: string
  branch_id: string
  program_id: string
  status: string
  submitted_at: string | null
  rejection_reason?: string | null
  created_at: string
  program_name?: string | null
  branch_name?: string | null
  applicant_full_name?: string | null
  consulting_agency_id?: string | null
  consulting_agency_name?: string | null
}

const toast = useToast()
const auth = useAuthStore()
const canSeeConsulting = computed(() => auth.isConsulting)
const { ask } = useConfirm()
const router = useRouter()
const route = useRoute()
const panelPrefix = computed(() => {
  if (route.path.startsWith('/operator/')) return '/operator'
  if (route.path.startsWith('/accountant/')) return '/accountant'
  return '/admin'
})
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')
const isAccountantPanel = computed(() => panelPrefix.value === '/accountant')

const items = ref<Application[]>([])
const total = ref(0)
const loading = ref(false)
const stats = ref<Record<string, number>>({
  total: 0, topshirildi: 0, korib_chiqilmoqda: 0, qabul_qilindi: 0, rad_etildi: 0,
})

const bulk = useBulkSelect<Application>(() => items.value)
const bulkBusy = ref(false)

// Filters persisted in URL so back/forward and sharing work.
const { filters, clear: clearAllFilters } = useUrlFilters({
  status: '' as string,
  admission_type: '' as string,
  branch_id: '' as string,
  education_level_id: '' as string,
  education_form_id: '' as string,
  program_id: '' as string,
  consulting_agency_id: '' as string,
  registered_by_id: '' as string,   // operator filter (admin/superadmin only)
  source_origin: '' as string,       // 'lead' | 'direct' | ''
  search: '' as string,
  page: 1,
  size: 20,
})

const branches = ref<any[]>([])
const educationLevels = ref<any[]>([])
const educationForms = ref<any[]>([])
const programs = ref<any[]>([])
const consultingAgencies = ref<ConsultingAgency[]>([])
const agencyOptions = computed(() =>
  consultingAgencies.value.map(a => ({ id: a.id, label: a.name })),
)

const branchOptions = computed(() => branches.value.map((b: any) => ({ id: b.id, label: b.name })))
const levelOptions  = computed(() => educationLevels.value.map((l: any) => ({ id: l.id, label: l.name })))
const formOptions   = computed(() => educationForms.value.map((f: any) => ({ id: f.id, label: f.name })))
const programOptions = computed(() => {
  let list = programs.value as any[]
  if (filters.branch_id) list = list.filter((p) => p.branch_id === filters.branch_id)
  if (filters.education_level_id) list = list.filter((p) => p.education_level_id === filters.education_level_id)
  if (filters.education_form_id) list = list.filter((p) => p.education_form_id === filters.education_form_id)
  return list.map((p: any) => ({ id: p.id, label: p.name, sub: p.code || '' }))
})

const STATUS_OPTIONS = [
  { id: 'topshirildi',       label: APPLICATION_STATUS.topshirildi },
  { id: 'korib_chiqilmoqda', label: APPLICATION_STATUS.korib_chiqilmoqda },
  { id: 'qabul_qilindi',     label: APPLICATION_STATUS.qabul_qilindi },
  { id: 'rad_etildi',        label: APPLICATION_STATUS.rad_etildi },
]
const TYPE_OPTIONS = [
  { id: 'yangi_qabul', label: ADMISSION_TYPE.yangi_qabul },
  { id: 'perevod',     label: ADMISSION_TYPE.perevod },
]
const SOURCE_OPTIONS = [
  { id: 'lead',   label: "Lead'dan o'tkazildi" },
  { id: 'direct', label: "To'g'ridan-to'g'ri yaratildi" },
]

// Operator pool for the "Operator" filter. Shown on every staff panel
// — admin/superadmin to slice by colleagues, operator to find a
// specific operator's work or pick out their own.
const operatorOptions = ref<Array<{ id: string; label: string }>>([])
async function loadOperators() {
  try {
    const us = await adminApi.users.list({ role: 'operator', size: 100 }).catch(() => null)
    if (us) {
      operatorOptions.value = us.items.map(u => ({
        id: u.id,
        label: u.full_name || u.phone || u.id.slice(0, 8),
      }))
    }
  } catch { /* ignore */ }
}

const activeFilterCount = computed(() => {
  let n = 0
  if (filters.status) n++
  if (filters.admission_type) n++
  if (filters.branch_id) n++
  if (filters.education_level_id) n++
  if (filters.education_form_id) n++
  if (filters.program_id) n++
  if (filters.consulting_agency_id) n++
  if (filters.registered_by_id) n++
  if (filters.source_origin) n++
  return n
})

function clearFilters() {
  clearAllFilters()
}

async function loadStats() {
  try { stats.value = await adminApi.applications.stats() } catch { /* ignore */ }
}

const exporting = ref(false)
async function exportXlsx() {
  exporting.value = true
  try {
    await downloadFile('/applications/export.xlsx', {
      status: filters.status || undefined,
      admission_type: filters.admission_type || undefined,
      branch_id: filters.branch_id || undefined,
      education_level_id: filters.education_level_id || undefined,
      education_form_id: filters.education_form_id || undefined,
      program_id: filters.program_id || undefined,
      consulting_agency_id: canSeeConsulting.value ? (filters.consulting_agency_id || undefined) : undefined,
    }, {
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      fallbackName: `arizalar-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')}.xlsx`,
    })
    toast.success("Excel yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.applications.list({
      status: filters.status || undefined,
      admission_type: filters.admission_type || undefined,
      branch_id: filters.branch_id || undefined,
      education_level_id: filters.education_level_id || undefined,
      education_form_id: filters.education_form_id || undefined,
      program_id: filters.program_id || undefined,
      consulting_agency_id: canSeeConsulting.value
        ? (filters.consulting_agency_id || undefined)
        : undefined,
      // Phase 2: no implicit panel-based scoping. Operators see the
      // full list by default; they use the Operator dropdown to filter
      // to their own work (or a colleague's) explicitly.
      registered_by_id: filters.registered_by_id || undefined,
      source: (filters.source_origin as any) || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items as Application[]
    total.value = res.total
    bulk.clear()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  if (!filters.search.trim()) return items.value
  const q = filters.search.toLowerCase()
  return items.value.filter((a) =>
    (a.application_number || '').toLowerCase().includes(q) ||
    (a.applicant_full_name || '').toLowerCase().includes(q) ||
    (a.program_name || '').toLowerCase().includes(q),
  )
})

watch(() => filters.status, () => { filters.page = 1; load() })
watch(() => filters.admission_type, () => { filters.page = 1; load() })
watch(() => filters.branch_id, () => {
  // narrow program selection if it no longer matches
  if (filters.program_id && !programOptions.value.some((p) => p.id === filters.program_id)) filters.program_id = ''
  filters.page = 1; load()
})
watch(() => filters.education_level_id, () => {
  if (filters.program_id && !programOptions.value.some((p) => p.id === filters.program_id)) filters.program_id = ''
  filters.page = 1; load()
})
watch(() => filters.education_form_id, () => {
  if (filters.program_id && !programOptions.value.some((p) => p.id === filters.program_id)) filters.program_id = ''
  filters.page = 1; load()
})
watch(() => filters.program_id, () => { filters.page = 1; load() })
watch(() => filters.consulting_agency_id, () => { filters.page = 1; load() })
watch(() => filters.registered_by_id, () => { filters.page = 1; load() })
watch(() => filters.source_origin, () => { filters.page = 1; load() })
watch(() => filters.page, load)

onMounted(async () => {
  const [b, lvl, frm, prg] = await Promise.all([
    adminApi.branches.list(false).catch(() => []),
    adminApi.educationLevels.list().catch(() => []),
    adminApi.educationForms.list().catch(() => []),
    adminApi.programs.list({ active_only: false }).catch(() => []),
  ])
  branches.value = b
  educationLevels.value = lvl
  educationForms.value = frm
  programs.value = prg

  if (canSeeConsulting.value) {
    consultingAgencies.value = await consultingApi.list(false).catch(() => [])
  }

  await Promise.all([load(), loadStats(), loadOperators()])
})

async function startReview(a: Application) {
  try {
    await adminApi.applications.startReview(a.id)
    toast.success("Ko'rib chiqishga olindi")
    await Promise.all([load(), loadStats()])
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function approve(a: Application) {
  const ok = await ask({
    title: "Arizani qabul qilish",
    message: `${a.application_number} qabul qilinsinmi?`,
    confirmLabel: "Qabul qilish",
    tone: 'primary',
  })
  if (!ok) return
  try {
    await adminApi.applications.review(a.id, { approved: true })
    toast.success("Qabul qilindi")
    await Promise.all([load(), loadStats()])
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function reject(a: Application) {
  const reason = window.prompt("Rad etish sababi (ixtiyoriy):") || ''
  const ok = await ask({
    title: "Arizani rad etish",
    message: `${a.application_number} rad etilsinmi?`,
    confirmLabel: "Rad etish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.applications.review(a.id, { approved: false, rejection_reason: reason || undefined })
    toast.success("Rad etildi")
    await Promise.all([load(), loadStats()])
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function remove(a: Application) {
  const ok = await ask({
    title: "Arizani o'chirish",
    message: `${a.application_number} o'chirilsinmi?`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.applications.delete(a.id)
    toast.success("O'chirildi")
    await Promise.all([load(), loadStats()])
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi (shartnoma bog'langan)")
  }
}

function setStatusFilter(s: string) {
  filters.status = filters.status === s ? '' : s
}

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

// Status visual maps — sober palette, status colors only on accent bars + pills
const STATUS_BAR: Record<string, string> = {
  topshirildi:        'bg-amber-500',
  korib_chiqilmoqda:  'bg-indigo-500',
  qabul_qilindi:      'bg-emerald-500',
  rad_etildi:         'bg-rose-500',
}
const STATUS_PILL: Record<string, string> = {
  topshirildi:        'bg-amber-50 text-amber-700 ring-1 ring-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-700/40',
  korib_chiqilmoqda:  'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:ring-indigo-700/40',
  qabul_qilindi:      'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-700/40',
  rad_etildi:         'bg-rose-50 text-rose-700 ring-1 ring-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:ring-rose-700/40',
}
const STATUS_DOT: Record<string, string> = {
  topshirildi: 'bg-amber-500', korib_chiqilmoqda: 'bg-indigo-500',
  qabul_qilindi: 'bg-emerald-500', rad_etildi: 'bg-rose-500',
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
function initials(fullName: string | null | undefined, fallback: string): string {
  if (!fullName) return fallback.slice(0, 2).toUpperCase()
  const parts = fullName.split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
}
function relativeTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return "Bugun"
  if (days === 1) return "Kecha"
  if (days < 7) return `${days} kun oldin`
  return d.toLocaleDateString('uz-UZ')
}

const reviewedPercent = computed(() => {
  const total = stats.value.total || 0
  if (!total) return 0
  return Math.round(((stats.value.qabul_qilindi || 0) + (stats.value.rad_etildi || 0)) / total * 100)
})

async function bulkDeleteSelected() {
  const ids = bulk.selectedIds.value
  if (!ids.length) return
  const ok = await ask({
    title: `${ids.length} ta ariza o'chirilsinmi?`,
    message: "Shartnomalari, to'lovlari va status tarixi ham o'chiriladi (cascade). Bu amalni qaytarib bo'lmaydi.",
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  bulkBusy.value = true
  try {
    const res = await adminApi.applications.bulkDelete(ids)
    toast.success(`${res.deleted} ta o'chirildi${res.skipped ? `, ${res.skipped} ta o'tkazib yuborildi` : ''}`)
    await Promise.all([load(), loadStats()])
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string }; detail?: string }>
    toast.error(ax.response?.data?.error?.message || ax.response?.data?.detail || "Xatolik")
  } finally {
    bulkBusy.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Arizalar"
      subtitle="Abituriyentlardan kelgan arizalarni ko'rib chiqing va boshqaring"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'Qabul jarayoni' }]"
    >
      <div class="hidden md:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mr-2">
        <span>Tahlil qilingan</span>
        <strong class="text-slate-900 dark:text-slate-100">{{ reviewedPercent }}%</strong>
      </div>
      <button class="btn-outline" :disabled="exporting" @click="exportXlsx"
              title="Filtr qoʻllangan barcha arizalarni Excel jadvali (.xlsx) sifatida yuklab olish — hamma ustun bilan, sarlavhasi rangli">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'Excel' }}
      </button>
      <RouterLink v-if="!isAccountantPanel" :to="`${panelPrefix}/applications/new`" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi ariza
      </RouterLink>
    </PageHeader>

    <!-- Stats tiles — tinted bg per status -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
      <!-- Total -->
      <button type="button"
              class="relative overflow-hidden rounded-2xl p-4 text-left transition-all border
                     bg-gradient-to-br from-violet-50 to-fuchsia-50
                     hover:shadow-lg hover:-translate-y-0.5
                     dark:from-violet-900/30 dark:to-fuchsia-900/20"
              :class="!filters.status
                ? 'border-violet-400 ring-2 ring-violet-300/60 shadow-md'
                : 'border-violet-200/70 dark:border-violet-700/40'"
              @click="filters.status = ''">
        <div class="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-violet-200/40 dark:bg-violet-700/20 blur-xl"></div>
        <div class="relative flex items-center justify-between">
          <div class="grid place-items-center w-9 h-9 rounded-xl bg-violet-500 text-white shadow-sm">
            <Inbox class="w-4 h-4" />
          </div>
          <ArrowUpRight class="w-4 h-4 text-violet-400" />
        </div>
        <div class="relative mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{{ stats.total || 0 }}</div>
        <div class="relative text-[11px] uppercase tracking-wider text-violet-700 dark:text-violet-300 mt-0.5 font-semibold">Jami arizalar</div>
      </button>

      <!-- Yangi (topshirildi) -->
      <button type="button"
              class="relative overflow-hidden rounded-2xl p-4 text-left transition-all border
                     bg-gradient-to-br from-amber-50 to-orange-50
                     hover:shadow-lg hover:-translate-y-0.5
                     dark:from-amber-900/30 dark:to-orange-900/20"
              :class="filters.status === 'topshirildi'
                ? 'border-amber-400 ring-2 ring-amber-300/60 shadow-md'
                : 'border-amber-200/70 dark:border-amber-700/40'"
              @click="setStatusFilter('topshirildi')">
        <div class="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-amber-200/40 dark:bg-amber-700/20 blur-xl"></div>
        <div class="relative flex items-center justify-between">
          <div class="grid place-items-center w-9 h-9 rounded-xl bg-amber-500 text-white shadow-sm">
            <Clock class="w-4 h-4" />
          </div>
          <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
        </div>
        <div class="relative mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{{ stats.topshirildi || 0 }}</div>
        <div class="relative text-[11px] uppercase tracking-wider text-amber-700 dark:text-amber-300 mt-0.5 font-semibold">Yangi</div>
      </button>

      <!-- Ko'rilmoqda -->
      <button type="button"
              class="relative overflow-hidden rounded-2xl p-4 text-left transition-all border
                     bg-gradient-to-br from-indigo-50 to-blue-50
                     hover:shadow-lg hover:-translate-y-0.5
                     dark:from-indigo-900/30 dark:to-blue-900/20"
              :class="filters.status === 'korib_chiqilmoqda'
                ? 'border-indigo-400 ring-2 ring-indigo-300/60 shadow-md'
                : 'border-indigo-200/70 dark:border-indigo-700/40'"
              @click="setStatusFilter('korib_chiqilmoqda')">
        <div class="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-indigo-200/40 dark:bg-indigo-700/20 blur-xl"></div>
        <div class="relative flex items-center justify-between">
          <div class="grid place-items-center w-9 h-9 rounded-xl bg-indigo-500 text-white shadow-sm">
            <Eye class="w-4 h-4" />
          </div>
          <ArrowUpRight class="w-4 h-4 text-indigo-400" />
        </div>
        <div class="relative mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{{ stats.korib_chiqilmoqda || 0 }}</div>
        <div class="relative text-[11px] uppercase tracking-wider text-indigo-700 dark:text-indigo-300 mt-0.5 font-semibold">Ko'rilmoqda</div>
      </button>

      <!-- Qabul qilindi -->
      <button type="button"
              class="relative overflow-hidden rounded-2xl p-4 text-left transition-all border
                     bg-gradient-to-br from-emerald-50 to-teal-50
                     hover:shadow-lg hover:-translate-y-0.5
                     dark:from-emerald-900/30 dark:to-teal-900/20"
              :class="filters.status === 'qabul_qilindi'
                ? 'border-emerald-400 ring-2 ring-emerald-300/60 shadow-md'
                : 'border-emerald-200/70 dark:border-emerald-700/40'"
              @click="setStatusFilter('qabul_qilindi')">
        <div class="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-emerald-200/40 dark:bg-emerald-700/20 blur-xl"></div>
        <div class="relative flex items-center justify-between">
          <div class="grid place-items-center w-9 h-9 rounded-xl bg-emerald-500 text-white shadow-sm">
            <FileCheck class="w-4 h-4" />
          </div>
          <ArrowUpRight class="w-4 h-4 text-emerald-400" />
        </div>
        <div class="relative mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{{ stats.qabul_qilindi || 0 }}</div>
        <div class="relative text-[11px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300 mt-0.5 font-semibold">Qabul qilindi</div>
      </button>

      <!-- Rad etildi -->
      <button type="button"
              class="relative overflow-hidden rounded-2xl p-4 text-left transition-all border
                     bg-gradient-to-br from-rose-50 to-red-50
                     hover:shadow-lg hover:-translate-y-0.5
                     dark:from-rose-900/30 dark:to-red-900/20"
              :class="filters.status === 'rad_etildi'
                ? 'border-rose-400 ring-2 ring-rose-300/60 shadow-md'
                : 'border-rose-200/70 dark:border-rose-700/40'"
              @click="setStatusFilter('rad_etildi')">
        <div class="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-rose-200/40 dark:bg-rose-700/20 blur-xl"></div>
        <div class="relative flex items-center justify-between">
          <div class="grid place-items-center w-9 h-9 rounded-xl bg-rose-500 text-white shadow-sm">
            <FileX class="w-4 h-4" />
          </div>
          <ArrowUpRight class="w-4 h-4 text-rose-400" />
        </div>
        <div class="relative mt-3 text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{{ stats.rad_etildi || 0 }}</div>
        <div class="relative text-[11px] uppercase tracking-wider text-rose-700 dark:text-rose-300 mt-0.5 font-semibold">Rad etildi</div>
      </button>
    </div>

    <!-- Filter bar -->
    <div class="card p-4 mb-4 flex flex-col gap-3">
      <div class="w-full flex items-center justify-between">
        <div class="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          <FilterIcon class="w-3.5 h-3.5" /> Filtrlar
          <span v-if="activeFilterCount" class="px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px]">
            {{ activeFilterCount }}
          </span>
        </div>
        <button v-if="activeFilterCount || filters.search" type="button"
                class="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1"
                @click="clearFilters">
          <XIcon class="w-3 h-3" /> Tozalash
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 w-full">
        <div class="lg:col-span-2">
          <label class="field-label">Qidirish</label>
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input v-model="filters.search" class="input pl-10" placeholder="Ariza №, abituriyent yoki yo'nalish..." />
          </div>
        </div>
        <div>
          <label class="field-label">Holati</label>
          <SearchSelect v-model="filters.status" :options="STATUS_OPTIONS" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Qabul turi</label>
          <SearchSelect v-model="filters.admission_type" :options="TYPE_OPTIONS" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Filial</label>
          <SearchSelect v-model="filters.branch_id" :options="branchOptions" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Ta'lim darajasi</label>
          <SearchSelect v-model="filters.education_level_id" :options="levelOptions" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Ta'lim shakli</label>
          <SearchSelect v-model="filters.education_form_id" :options="formOptions" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Yo'nalish</label>
          <SearchSelect v-model="filters.program_id" :options="programOptions" placeholder="— hammasi —" allow-clear />
        </div>
        <div v-if="canSeeConsulting">
          <label class="field-label">Konsalting</label>
          <SearchSelect v-model="filters.consulting_agency_id" :options="agencyOptions" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Operator</label>
          <SearchSelect v-model="filters.registered_by_id" :options="operatorOptions" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Manba</label>
          <SearchSelect v-model="filters.source_origin" :options="SOURCE_OPTIONS" placeholder="— hammasi —" allow-clear />
        </div>
      </div>
    </div>

    <!-- List -->
    <Skeleton v-if="loading" type="table" />

    <div v-else-if="!filtered.length" class="card p-6">
      <EmptyState :icon="ClipboardList"
                  title="Arizalar topilmadi"
                  :subtitle="filters.search || filters.status ? 'Filterlarni tozalab ko\'ring' : 'Birinchi arizani yarating'">
        <RouterLink v-if="!isAccountantPanel" :to="`${panelPrefix}/applications/new`" class="btn-primary mt-4 inline-flex">
          <Plus class="w-4 h-4" /> Yangi ariza
        </RouterLink>
      </EmptyState>
    </div>

    <div v-else class="card">
      <div class="overflow-x-auto rounded-t-2xl">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-slate-50 dark:bg-slate-900/60 border-b border-slate-200 dark:border-slate-800
                       text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
              <th class="w-1"></th>
              <th v-if="!isOperatorPanel && !isAccountantPanel" class="w-8 px-3 py-3">
                <input type="checkbox" class="rounded cursor-pointer"
                       :checked="bulk.allSelected.value"
                       :indeterminate.prop="bulk.partial.value"
                       @change="bulk.toggleAll()" />
              </th>
              <th class="text-left font-semibold px-4 py-3">Abituriyent</th>
              <th class="text-left font-semibold px-4 py-3">Yo'nalish</th>
              <th class="text-left font-semibold px-4 py-3 w-32">Qabul turi</th>
              <th v-if="!isOperatorPanel" class="text-left font-semibold px-4 py-3 w-36">Operator</th>
              <th class="text-left font-semibold px-4 py-3 w-24">Manba</th>
              <th class="text-left font-semibold px-4 py-3 w-44">Holati</th>
              <th class="text-left font-semibold px-4 py-3 w-32">Sana</th>
              <th class="text-right font-semibold px-4 py-3 w-44">Amal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in filtered" :key="a.id"
                class="border-b border-slate-100 dark:border-slate-800/60
                       hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors cursor-pointer group"
                :class="bulk.isSelected(a.id) ? 'bg-brand-50/40 dark:bg-brand-500/10' : ''"
                @click="router.push(`${panelPrefix}/applications/${a.id}`)">
              <!-- Status ribbon -->
              <td class="p-0">
                <div class="w-1 h-12 rounded-r-full" :class="STATUS_BAR[a.status] || 'bg-slate-300 dark:bg-slate-700'"></div>
              </td>

              <td v-if="!isOperatorPanel && !isAccountantPanel" class="px-3 py-3" @click.stop>
                <input type="checkbox" class="rounded cursor-pointer"
                       :checked="bulk.isSelected(a.id)"
                       @change="bulk.toggle(a.id)" />
              </td>

              <!-- Abituriyent -->
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <div class="avatar w-9 h-9 text-xs bg-gradient-to-br text-white shadow-sm" :class="avatarColor(a.applicant_id)">
                    {{ initials(a.applicant_full_name, a.applicant_id) }}
                  </div>
                  <div class="min-w-0">
                    <div class="font-semibold text-slate-900 dark:text-slate-100 truncate transition-colors">
                      {{ a.applicant_full_name || a.applicant_id.slice(0, 8) }}
                    </div>
                    <div class="font-mono text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      <span class="text-slate-400">№</span> {{ a.application_number }}
                    </div>
                  </div>
                </div>
              </td>

              <!-- Yo'nalish -->
              <td class="px-4 py-3 min-w-0">
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate max-w-[280px]">{{ a.program_name || '—' }}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[280px]">{{ a.branch_name || '—' }}</div>
              </td>

              <!-- Qabul turi -->
              <td class="px-4 py-3">
                <span class="pill">{{ tr(ADMISSION_TYPE, a.admission_type) }}</span>
              </td>

              <!-- Operator (registered_by) — hidden on operator's own panel -->
              <td v-if="!isOperatorPanel" class="px-4 py-3">
                <span v-if="(a as any).applicant_registered_by_name"
                      class="text-xs text-slate-700 dark:text-slate-300 truncate inline-block max-w-[140px]">
                  {{ (a as any).applicant_registered_by_name }}
                </span>
                <span v-else class="text-slate-400 text-xs">—</span>
              </td>

              <!-- Manba: Lead'dan o'tkazildi vs to'g'ridan-to'g'ri -->
              <td class="px-4 py-3">
                <span v-if="(a as any).lead_id"
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/70 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-700/40"
                      title="Lead'dan o'tkazildi">
                  Lead
                </span>
                <span v-else
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:ring-slate-700/60"
                      title="To'g'ridan-to'g'ri yaratildi">
                  Bevosita
                </span>
              </td>

              <!-- Status -->
              <td class="px-4 py-3">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold"
                      :class="STATUS_PILL[a.status] || ''">
                  <span class="w-1.5 h-1.5 rounded-full" :class="STATUS_DOT[a.status] || 'bg-slate-400'"></span>
                  {{ tr(APPLICATION_STATUS, a.status) }}
                </span>
              </td>

              <!-- Sana -->
              <td class="px-4 py-3">
                <div class="text-xs text-slate-600 dark:text-slate-400 inline-flex items-center gap-1">
                  <Clock class="w-3 h-3" />
                  {{ relativeTime(a.submitted_at || a.created_at) }}
                </div>
              </td>

              <!-- Amal: primary CTA + kebab -->
              <td class="px-4 py-3" @click.stop>
                <div class="flex items-center justify-end gap-1.5">
                  <!-- Contextual primary -->
                  <button v-if="a.status === 'topshirildi'"
                          class="btn-outline btn-sm"
                          @click="startReview(a)">
                    <PlayCircle class="w-3.5 h-3.5" /> Ko'rish
                  </button>
                  <button v-else-if="a.status === 'korib_chiqilmoqda'"
                          class="btn-primary btn-sm"
                          @click="approve(a)">
                    <CheckCircle2 class="w-3.5 h-3.5" /> Qabul
                  </button>
                  <RouterLink v-else
                              :to="`${panelPrefix}/applications/${a.id}`"
                              class="btn-outline btn-sm">
                    <Eye class="w-3.5 h-3.5" /> Batafsil
                  </RouterLink>

                  <!-- Kebab dropdown -->
                  <Dropdown align="right">
                    <template #trigger>
                      <button class="icon-btn" title="Ko'proq amallar">
                        <MoreVertical class="w-4 h-4" />
                      </button>
                    </template>
                    <RouterLink :to="`${panelPrefix}/applications/${a.id}`" class="menu-item">
                      <Eye class="w-4 h-4 text-slate-500" /> Batafsil
                    </RouterLink>
                    <RouterLink v-if="!isAccountantPanel" :to="`${panelPrefix}/applications/${a.id}/edit`" class="menu-item">
                      <Pencil class="w-4 h-4 text-slate-500" /> Tahrirlash
                    </RouterLink>
                    <template v-if="!isAccountantPanel">
                      <div v-if="a.status === 'topshirildi' || a.status === 'korib_chiqilmoqda'" class="menu-divider"></div>
                      <button v-if="a.status === 'topshirildi'" class="menu-item" @click="startReview(a)">
                        <PlayCircle class="w-4 h-4 text-sky-500" /> Ko'rib chiqishga olish
                      </button>
                      <button v-if="a.status === 'topshirildi' || a.status === 'korib_chiqilmoqda'" class="menu-item" @click="approve(a)">
                        <CheckCircle2 class="w-4 h-4 text-emerald-500" /> Qabul qilish
                      </button>
                      <button v-if="a.status === 'topshirildi' || a.status === 'korib_chiqilmoqda'" class="menu-item" @click="reject(a)">
                        <XCircle class="w-4 h-4 text-rose-500" /> Rad etish
                      </button>
                    </template>
                    <template v-if="!isOperatorPanel && !isAccountantPanel">
                      <div class="menu-divider"></div>
                      <button class="menu-item !text-rose-600 dark:!text-rose-400 hover:!bg-rose-50 dark:hover:!bg-rose-900/30"
                              @click="remove(a)">
                        <Trash2 class="w-4 h-4" /> O'chirish
                      </button>
                    </template>
                  </Dropdown>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <Pagination v-if="items.length" v-model:page="filters.page" :last-page="lastPage()" :total="total" :size="filters.size" />
    </div>

    <BulkActionBar v-if="!isOperatorPanel && !isAccountantPanel"
                   :count="bulk.count.value"
                   :label="`${bulk.count.value} ta ariza tanlandi`"
                   @clear="bulk.clear()">
      <button type="button"
              class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition disabled:opacity-50"
              :disabled="bulkBusy"
              @click="bulkDeleteSelected">
        O'chirish
      </button>
    </BulkActionBar>
  </div>
</template>
