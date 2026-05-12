<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, Tooltip, Legend, CategoryScale, LinearScale,
  PointElement, LineElement, Filler,
} from 'chart.js'
import {
  Users, ClipboardList, FileText, Inbox, CreditCard,
  TrendingUp, RefreshCcw, X, Award, AlertTriangle, Download, Activity,
} from 'lucide-vue-next'
import {
  adminApi,
  type OperatorStatsRead,
  type OperatorTimeseriesRead,
  type OperatorActivityRead,
} from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import { useThemeStore } from '@/stores/theme'
import { AUDIT_ACTIONS, tr } from '@/utils/labels'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

ChartJS.register(Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Filler)

const toast = useToast()
const theme = useThemeStore()

// ---------- Date range ----------
type Preset = 'today' | '7d' | '30d' | 'month' | 'custom'
const preset = ref<Preset>('30d')
const fromDate = ref<string>('')
const toDate = ref<string>('')

function isoDay(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function applyPreset(p: Preset) {
  preset.value = p
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  let from = new Date(today)
  if (p === 'today') {
    // from = today
  } else if (p === '7d') {
    from.setDate(today.getDate() - 6)
  } else if (p === '30d') {
    from.setDate(today.getDate() - 29)
  } else if (p === 'month') {
    from = new Date(today.getFullYear(), today.getMonth(), 1)
  }
  fromDate.value = isoDay(from)
  toDate.value = isoDay(today)
}

// Sync custom-date inputs → preset='custom'
function onCustomDate() {
  preset.value = 'custom'
}

// ---------- Data ----------
const loading = ref(false)
const items = ref<OperatorStatsRead[]>([])
// Previous-equivalent-period totals — drives the "+X% vs ..." pill on
// each summary StatCard. We compute the window length from the current
// range and shift backwards by exactly that many days.
const prevItems = ref<OperatorStatsRead[]>([])
const downloading = ref(false)

const drilldownId = ref<string | null>(null)
const drilldownLoading = ref(false)
const timeseries = ref<OperatorTimeseriesRead | null>(null)
const activity = ref<OperatorActivityRead | null>(null)

function prevWindow(): { from: string; to: string } {
  const from = new Date(fromDate.value)
  const to = new Date(toDate.value)
  const days = Math.round((to.getTime() - from.getTime()) / 86400000) + 1
  const prevTo = new Date(from)
  prevTo.setDate(prevTo.getDate() - 1)
  const prevFrom = new Date(prevTo)
  prevFrom.setDate(prevFrom.getDate() - days + 1)
  return { from: isoDay(prevFrom), to: isoDay(prevTo) }
}

async function loadLeaderboard() {
  if (!fromDate.value || !toDate.value) return
  loading.value = true
  try {
    const [res, prev] = await Promise.all([
      adminApi.analytics.leaderboard({ from: fromDate.value, to: toDate.value }),
      adminApi.analytics.leaderboard(prevWindow()),
    ])
    items.value = res.items
    prevItems.value = prev.items
  } catch {
    toast.error("Analitikani yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

async function loadDrilldown(opId: string) {
  drilldownLoading.value = true
  try {
    const [ts, act] = await Promise.all([
      adminApi.analytics.timeseries(opId, { from: fromDate.value, to: toDate.value }),
      adminApi.analytics.activity(opId, { from: fromDate.value, to: toDate.value, limit: 20 }),
    ])
    timeseries.value = ts
    activity.value = act
  } catch {
    toast.error("Operator ma'lumotlarini yuklab bo'lmadi")
  } finally {
    drilldownLoading.value = false
  }
}

async function downloadCsv() {
  if (!fromDate.value || !toDate.value) return
  downloading.value = true
  try {
    await adminApi.analytics.exportCsv({ from: fromDate.value, to: toDate.value })
    toast.success('CSV yuklab olindi')
  } catch {
    toast.error("CSV yuklab bo'lmadi")
  } finally {
    downloading.value = false
  }
}

function selectOperator(opId: string) {
  if (drilldownId.value === opId) {
    drilldownId.value = null
    timeseries.value = null
    activity.value = null
    return
  }
  drilldownId.value = opId
  loadDrilldown(opId)
}

// ---------- Sorting ----------
type SortKey = keyof OperatorStatsRead
const sortKey = ref<SortKey>('contracts_signed')
const sortDir = ref<'asc' | 'desc'>('desc')

function setSort(k: SortKey) {
  if (sortKey.value === k) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = k
    sortDir.value = 'desc'
  }
}

const sortedItems = computed(() => {
  const arr = [...items.value]
  const k = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return arr.sort((a, b) => {
    const av = a[k] as any
    const bv = b[k] as any
    if (typeof av === 'string' && typeof bv === 'string') {
      return av.localeCompare(bv) * dir
    }
    return ((Number(av) || 0) - (Number(bv) || 0)) * dir
  })
})

// Totals row across all visible operators (used by summary cards).
const NUMERIC_KEYS: SortKey[] = [
  'leads_created', 'leads_won', 'leads_lost', 'leads_open',
  'applicants_registered',
  'applications_created', 'applications_reviewed', 'applications_accepted', 'applications_rejected',
  'contracts_created', 'contracts_signed', 'contracts_cancelled',
  'payments_registered', 'payments_confirmed',
]
function sumTotals(rows: OperatorStatsRead[]): Record<string, number> {
  const t: Record<string, number> = {}
  for (const k of NUMERIC_KEYS) t[k] = 0
  let paid = 0
  for (const r of rows) {
    for (const k of NUMERIC_KEYS) t[k] += Number((r as any)[k]) || 0
    paid += Number(r.payments_confirmed_amount) || 0
  }
  t['payments_confirmed_amount'] = paid
  return t
}
const totals = computed(() => sumTotals(items.value))
const prevTotals = computed(() => sumTotals(prevItems.value))

// % change current vs previous equivalent period. Null when prev=0 and
// current=0 (no change to report); 100% when prev=0 and current>0 (new
// activity); otherwise (current-prev)/prev * 100.
function trendPct(key: string): number | null {
  const cur = totals.value[key] || 0
  const prev = prevTotals.value[key] || 0
  if (cur === 0 && prev === 0) return null
  if (prev === 0) return 100
  return Math.round(((cur - prev) / prev) * 100)
}

// ---------- Formatting ----------
function fmtMoney(v: string | number): string {
  const n = Number(v) || 0
  return n.toLocaleString('uz-UZ')
}

function roleLabel(role: string): string {
  return {
    superadmin: 'Super admin',
    admin: 'Admin',
    operator: 'Operator',
    director: 'Direktor',
    accountant: 'Buxgalter',
    applicant: 'Abituriyent',
  }[role] || role
}

const selectedOperator = computed(() =>
  drilldownId.value ? items.value.find(i => i.operator_id === drilldownId.value) || null : null
)

// ---------- Chart data ----------
const labelsForChart = computed(() => {
  if (!timeseries.value) return []
  return timeseries.value.leads_created.map(p => p.date.slice(5))  // MM-DD
})

const isDark = computed(() => theme.theme === 'dark')

function chartDataset(label: string, color: string, points: number[]) {
  return {
    label,
    data: points,
    borderColor: color,
    backgroundColor: color + '22',
    borderWidth: 2,
    pointRadius: 2,
    pointHoverRadius: 4,
    tension: 0.3,
    fill: true,
  }
}

const conversionChart = computed(() => {
  if (!timeseries.value) return { labels: [], datasets: [] }
  return {
    labels: labelsForChart.value,
    datasets: [
      chartDataset('Lead yaratildi', '#6366f1', timeseries.value.leads_created.map(p => p.value)),
      chartDataset('Lead konversiya', '#10b981', timeseries.value.leads_won.map(p => p.value)),
      chartDataset('Abituriyent', '#f59e0b', timeseries.value.applicants_registered.map(p => p.value)),
    ],
  }
})

const contractsChart = computed(() => {
  if (!timeseries.value) return { labels: [], datasets: [] }
  return {
    labels: labelsForChart.value,
    datasets: [
      chartDataset('Shartnoma yaratildi', '#0ea5e9', timeseries.value.contracts_created.map(p => p.value)),
      chartDataset('Imzolandi', '#22c55e', timeseries.value.contracts_signed.map(p => p.value)),
      chartDataset("To'lov tasdiqlandi", '#a855f7', timeseries.value.payments_confirmed.map(p => p.value)),
    ],
  }
})

const chartOpts = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index' as const, intersect: false },
  plugins: {
    legend: {
      labels: {
        color: isDark.value ? '#cbd5e1' : '#475569',
        usePointStyle: true,
        font: { size: 11 },
      },
    },
    tooltip: {
      backgroundColor: isDark.value ? '#0f172a' : '#fff',
      titleColor: isDark.value ? '#e2e8f0' : '#0f172a',
      bodyColor: isDark.value ? '#cbd5e1' : '#475569',
      borderColor: isDark.value ? '#334155' : '#e2e8f0',
      borderWidth: 1,
      padding: 10,
    },
  },
  scales: {
    x: {
      ticks: { color: isDark.value ? '#94a3b8' : '#64748b', font: { size: 10 } },
      grid: { display: false },
    },
    y: {
      beginAtZero: true,
      ticks: { color: isDark.value ? '#94a3b8' : '#64748b', font: { size: 10 }, precision: 0 },
      grid: { color: isDark.value ? '#1e293b' : '#f1f5f9' },
    },
  },
}))

onMounted(() => {
  applyPreset('30d')
  loadLeaderboard()
})

watch([fromDate, toDate], () => {
  loadLeaderboard()
  if (drilldownId.value) loadDrilldown(drilldownId.value)
})
</script>

<template>
  <div>
    <PageHeader title="Operatorlar analitikasi"
                subtitle="Har bir operator bo'yicha leadlar, arizalar, shartnomalar va to'lovlar bo'yicha jami ko'rsatkichlar." />

    <!-- Date range bar -->
    <section class="card p-4 mb-5">
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex flex-wrap items-center gap-1">
          <button v-for="(p, label) in {
                    today: 'Bugun',
                    '7d': "Oxirgi 7 kun",
                    '30d': 'Oxirgi 30 kun',
                    month: 'Joriy oy',
                  }"
                  :key="p"
                  type="button"
                  class="px-3 py-1.5 rounded-md text-xs font-medium transition"
                  :class="preset === p
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
                  @click="applyPreset(p as Preset)">
            {{ label }}
          </button>
        </div>

        <div class="hidden sm:block w-px h-6 bg-slate-200 dark:bg-slate-700 mx-1"></div>

        <div class="flex items-center gap-2 text-xs">
          <span class="text-slate-500 dark:text-slate-400">Dan:</span>
          <input v-model="fromDate" type="date" @change="onCustomDate"
                 class="px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          <span class="text-slate-500 dark:text-slate-400">Gacha:</span>
          <input v-model="toDate" type="date" @change="onCustomDate"
                 class="px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
        </div>

        <div class="ml-auto flex items-center gap-2">
          <button type="button"
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition disabled:opacity-50"
                  :disabled="downloading || loading || !items.length"
                  @click="downloadCsv">
            <Download class="w-3 h-3" :class="{ 'animate-pulse': downloading }" />
            CSV
          </button>
          <button type="button"
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
                  @click="loadLeaderboard">
            <RefreshCcw class="w-3 h-3" :class="{ 'animate-spin': loading }" />
            Yangilash
          </button>
        </div>
      </div>
    </section>

    <!-- Totals summary (with trend deltas vs the previous equivalent period) -->
    <section v-if="!loading && items.length" class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
      <StatCard label="Konversiyalar" :value="totals.leads_won" :icon="TrendingUp" tone="emerald"
                :trend="trendPct('leads_won')" trend-hint="oldingi davrga nisbatan"
                :hint="`${totals.leads_created} lead'dan`" />
      <StatCard label="Arizalar" :value="totals.applications_created" :icon="ClipboardList" tone="amber"
                :trend="trendPct('applications_created')" trend-hint="oldingi davrga nisbatan"
                :hint="`${totals.applications_accepted} qabul qilindi`" />
      <StatCard label="Imzolangan shartnomalar" :value="totals.contracts_signed" :icon="FileText" tone="brand"
                :trend="trendPct('contracts_signed')" trend-hint="oldingi davrga nisbatan"
                :hint="`${totals.contracts_created} yaratildi`" />
      <StatCard label="Tasdiqlangan to'lov" :value="fmtMoney(totals.payments_confirmed_amount) + ' so\'m'"
                :icon="CreditCard" tone="violet"
                :trend="trendPct('payments_confirmed_amount')" trend-hint="oldingi davrga nisbatan"
                :hint="`${totals.payments_confirmed} ta to'lov`" />
    </section>

    <!-- Leaderboard table -->
    <section class="card overflow-hidden">
      <div class="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <h2 class="section-title">Reyting</h2>
        <span v-if="!loading" class="text-xs text-slate-500 dark:text-slate-400">
          {{ items.length }} ta xodim
        </span>
      </div>

      <div v-if="loading" class="p-5 space-y-3">
        <Skeleton v-for="i in 5" :key="i" class="h-10" />
      </div>

      <div v-else-if="!items.length" class="p-10 text-center text-sm text-slate-500 dark:text-slate-400">
        Tanlangan oraliqda ma'lumot topilmadi
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 dark:bg-slate-800/50 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <tr>
              <th class="px-4 py-3 text-left font-semibold sticky left-0 bg-slate-50 dark:bg-slate-800/50 z-10">
                <button type="button" @click="setSort('full_name')" class="hover:text-brand-600">Xodim</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('leads_created')" class="hover:text-brand-600">Lead</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('leads_won')" class="hover:text-brand-600">Konv.</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('applicants_registered')" class="hover:text-brand-600">Abit.</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('applications_created')" class="hover:text-brand-600">Ariza</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('applications_reviewed')" class="hover:text-brand-600">Ko'rib chiqildi</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('contracts_created')" class="hover:text-brand-600">Shartnoma</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('contracts_signed')" class="hover:text-brand-600">Imzo.</button>
              </th>
              <th class="px-3 py-3 text-right font-semibold">
                <button type="button" @click="setSort('payments_confirmed')" class="hover:text-brand-600">To'lov</button>
              </th>
              <th class="px-4 py-3 text-right font-semibold">
                <button type="button" @click="setSort('payments_confirmed_amount')" class="hover:text-brand-600">Summa</button>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
            <tr v-for="row in sortedItems" :key="row.operator_id"
                class="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition"
                :class="drilldownId === row.operator_id ? 'bg-brand-50 dark:bg-brand-500/10' : ''"
                @click="selectOperator(row.operator_id)">
              <td class="px-4 py-3 sticky left-0 bg-white dark:bg-slate-900 z-10 group-hover:bg-slate-50"
                  :class="drilldownId === row.operator_id ? '!bg-brand-50 dark:!bg-brand-500/10' : ''">
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate max-w-[200px]">
                  {{ row.full_name || row.phone || row.operator_id.slice(0, 8) }}
                </div>
                <div class="text-[10px] text-slate-500 dark:text-slate-400">{{ roleLabel(row.role) }}</div>
              </td>
              <td class="px-3 py-3 text-right tabular-nums">{{ row.leads_created }}</td>
              <td class="px-3 py-3 text-right tabular-nums">
                <span :class="row.leads_won > 0 ? 'text-emerald-700 dark:text-emerald-300 font-semibold' : 'text-slate-400'">
                  {{ row.leads_won }}
                </span>
              </td>
              <td class="px-3 py-3 text-right tabular-nums">{{ row.applicants_registered }}</td>
              <td class="px-3 py-3 text-right tabular-nums">{{ row.applications_created }}</td>
              <td class="px-3 py-3 text-right tabular-nums">{{ row.applications_reviewed }}</td>
              <td class="px-3 py-3 text-right tabular-nums">{{ row.contracts_created }}</td>
              <td class="px-3 py-3 text-right tabular-nums">
                <span :class="row.contracts_signed > 0 ? 'text-brand-700 dark:text-brand-300 font-semibold' : 'text-slate-400'">
                  {{ row.contracts_signed }}
                </span>
              </td>
              <td class="px-3 py-3 text-right tabular-nums">{{ row.payments_confirmed }}</td>
              <td class="px-4 py-3 text-right tabular-nums font-medium text-slate-700 dark:text-slate-300">
                {{ fmtMoney(row.payments_confirmed_amount) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Drilldown panel -->
    <section v-if="selectedOperator" class="mt-6 card p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="section-title">
            {{ selectedOperator.full_name || selectedOperator.phone || 'Operator' }}
          </h2>
          <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {{ roleLabel(selectedOperator.role) }} · {{ fromDate }} → {{ toDate }}
          </div>
        </div>
        <button type="button" class="icon-btn"
                @click="drilldownId = null; timeseries = null">
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- KPI tiles for this operator -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <StatCard label="Leadlar" :value="selectedOperator.leads_created" :icon="Inbox" tone="amber"
                  :hint="`${selectedOperator.leads_won} konv. · ${selectedOperator.leads_lost} yo'q.`" />
        <StatCard label="Abituriyentlar" :value="selectedOperator.applicants_registered" :icon="Users" tone="violet" />
        <StatCard label="Imzolangan shartnoma" :value="selectedOperator.contracts_signed"
                  :icon="Award" tone="brand"
                  :hint="`${selectedOperator.contracts_cancelled} bekor`" />
        <StatCard :label="`To'lov (so'm)`"
                  :value="fmtMoney(selectedOperator.payments_confirmed_amount)"
                  :icon="CreditCard" tone="emerald"
                  :hint="`${selectedOperator.payments_confirmed} ta`" />
      </div>

      <div v-if="drilldownLoading" class="space-y-4">
        <Skeleton class="h-64" />
        <Skeleton class="h-64" />
      </div>

      <div v-else-if="timeseries" class="grid lg:grid-cols-2 gap-5">
        <div>
          <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
            <TrendingUp class="w-4 h-4 text-emerald-500" />
            Funnel: Lead → Abituriyent
          </h3>
          <div class="h-64">
            <Line :data="conversionChart" :options="chartOpts" />
          </div>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
            <FileText class="w-4 h-4 text-brand-500" />
            Shartnoma va to'lovlar
          </h3>
          <div class="h-64">
            <Line :data="contractsChart" :options="chartOpts" />
          </div>
        </div>
      </div>

      <!-- Lead → Application → Contract conversion bar -->
      <div v-if="!drilldownLoading" class="mt-6 grid lg:grid-cols-2 gap-5">
        <div class="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40">
          <div class="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
            <AlertTriangle v-if="selectedOperator.leads_created && !selectedOperator.contracts_signed"
                           class="w-3.5 h-3.5 text-amber-500" />
            Konversiya foizi
          </div>
          <div class="grid grid-cols-3 gap-3 text-sm">
            <div>
              <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Lead → Abituriyent</div>
              <div class="text-xl font-bold tabular-nums">
                {{ selectedOperator.leads_created
                   ? Math.round((selectedOperator.leads_won / selectedOperator.leads_created) * 100)
                   : 0 }}%
              </div>
            </div>
            <div>
              <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Ariza → Qabul</div>
              <div class="text-xl font-bold tabular-nums">
                {{ selectedOperator.applications_reviewed
                   ? Math.round((selectedOperator.applications_accepted / selectedOperator.applications_reviewed) * 100)
                   : 0 }}%
              </div>
            </div>
            <div>
              <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Shartnoma → Imzo</div>
              <div class="text-xl font-bold tabular-nums">
                {{ selectedOperator.contracts_created
                   ? Math.round((selectedOperator.contracts_signed / selectedOperator.contracts_created) * 100)
                   : 0 }}%
              </div>
            </div>
          </div>
        </div>

        <!-- Audit-log activity breakdown — what the operator actually did. -->
        <div class="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40">
          <div class="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center justify-between gap-2">
            <span class="inline-flex items-center gap-2">
              <Activity class="w-3.5 h-3.5 text-sky-500" />
              Faollik (audit jurnali)
            </span>
            <span v-if="activity" class="text-[10px] text-slate-500 dark:text-slate-400 tabular-nums">
              {{ activity.total }} ta yozuv
            </span>
          </div>
          <div v-if="!activity || !activity.rows.length"
               class="text-xs text-slate-500 dark:text-slate-400 py-4 text-center">
            Tanlangan oraliqda faollik yo'q
          </div>
          <ul v-else class="space-y-1.5 max-h-64 overflow-y-auto pr-1">
            <li v-for="row in activity.rows" :key="row.action"
                class="flex items-center gap-3 text-sm">
              <div class="flex-1 min-w-0">
                <div class="text-slate-700 dark:text-slate-300 truncate">
                  {{ tr(AUDIT_ACTIONS, row.action) }}
                </div>
                <!-- Show raw key only when no translation found, so admins
                     can spot new actions worth labelling. -->
                <div v-if="!AUDIT_ACTIONS[row.action]"
                     class="text-[10px] font-mono text-slate-400 truncate">
                  {{ row.action }}
                </div>
              </div>
              <span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 tabular-nums shrink-0">
                {{ row.count }}
              </span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>
