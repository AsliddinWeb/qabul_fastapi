<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, Tooltip, Legend, CategoryScale, LinearScale,
  PointElement, LineElement, Filler,
} from 'chart.js'
import {
  Users, ClipboardList, FileText, Inbox, CreditCard,
  TrendingUp, RefreshCcw, X, Award, AlertTriangle,
} from 'lucide-vue-next'
import { adminApi, type OperatorStatsRead, type OperatorTimeseriesRead } from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import { useThemeStore } from '@/stores/theme'
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

const drilldownId = ref<string | null>(null)
const drilldownLoading = ref(false)
const timeseries = ref<OperatorTimeseriesRead | null>(null)

async function loadLeaderboard() {
  if (!fromDate.value || !toDate.value) return
  loading.value = true
  try {
    const res = await adminApi.analytics.leaderboard({ from: fromDate.value, to: toDate.value })
    items.value = res.items
  } catch {
    toast.error("Analitikani yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

async function loadTimeseries(opId: string) {
  drilldownLoading.value = true
  try {
    timeseries.value = await adminApi.analytics.timeseries(opId, {
      from: fromDate.value,
      to: toDate.value,
    })
  } catch {
    toast.error("Operator ma'lumotlarini yuklab bo'lmadi")
  } finally {
    drilldownLoading.value = false
  }
}

function selectOperator(opId: string) {
  if (drilldownId.value === opId) {
    drilldownId.value = null
    timeseries.value = null
    return
  }
  drilldownId.value = opId
  loadTimeseries(opId)
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

// Totals row across all visible operators
const totals = computed(() => {
  const t: Record<string, number> = {}
  const numericKeys: SortKey[] = [
    'leads_created', 'leads_won', 'leads_lost', 'leads_open',
    'applicants_registered',
    'applications_created', 'applications_reviewed', 'applications_accepted', 'applications_rejected',
    'contracts_created', 'contracts_signed', 'contracts_cancelled',
    'payments_registered', 'payments_confirmed',
  ]
  for (const k of numericKeys) t[k] = 0
  let paid = 0
  for (const r of items.value) {
    for (const k of numericKeys) t[k] += Number((r as any)[k]) || 0
    paid += Number(r.payments_confirmed_amount) || 0
  }
  t['payments_confirmed_amount'] = paid
  return t
})

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
  if (drilldownId.value) loadTimeseries(drilldownId.value)
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

        <div class="ml-auto">
          <button type="button"
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
                  @click="loadLeaderboard">
            <RefreshCcw class="w-3 h-3" :class="{ 'animate-spin': loading }" />
            Yangilash
          </button>
        </div>
      </div>
    </section>

    <!-- Totals summary -->
    <section v-if="!loading && items.length" class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
      <StatCard label="Konversiyalar" :value="totals.leads_won" :icon="TrendingUp" tone="emerald"
                :hint="`${totals.leads_created} lead'dan`" />
      <StatCard label="Arizalar" :value="totals.applications_created" :icon="ClipboardList" tone="amber"
                :hint="`${totals.applications_accepted} qabul qilindi`" />
      <StatCard label="Imzolangan shartnomalar" :value="totals.contracts_signed" :icon="FileText" tone="brand"
                :hint="`${totals.contracts_created} yaratildi`" />
      <StatCard label="Tasdiqlangan to'lov" :value="fmtMoney(totals.payments_confirmed_amount) + ' so\'m'"
                :icon="CreditCard" tone="violet"
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
      <div v-if="!drilldownLoading" class="mt-6 p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40">
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
    </section>
  </div>
</template>
