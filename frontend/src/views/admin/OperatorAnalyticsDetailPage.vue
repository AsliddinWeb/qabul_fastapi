<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, Tooltip, Legend, CategoryScale, LinearScale,
  PointElement, LineElement, Filler,
} from 'chart.js'
import {
  Users, FileText, Inbox, CreditCard,
  TrendingUp, RefreshCcw, Award, AlertTriangle, ArrowLeft, Activity, Phone,
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

const route = useRoute()
const toast = useToast()
const theme = useThemeStore()

const operatorId = computed(() => route.params.id as string)
const panelPrefix = computed(() => {
  if (route.path.startsWith('/director/')) return '/director'
  return '/admin'
})

// ---------- Date range (same presets as leaderboard) ----------
type Preset = 'today' | '7d' | '30d' | 'month' | 'custom'
const PRESET_LABELS: { key: Preset; label: string }[] = [
  { key: 'today', label: 'Bugun' },
  { key: '7d',    label: 'Oxirgi 7 kun' },
  { key: '30d',   label: 'Oxirgi 30 kun' },
  { key: 'month', label: 'Joriy oy' },
]
const preset = ref<Preset>('30d')
const fromDate = ref<string>('')
const toDate = ref<string>('')

function isoDay(d: Date): string { return d.toISOString().slice(0, 10) }
function applyPreset(p: Preset) {
  preset.value = p
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  let from = new Date(today)
  if (p === '7d') from.setDate(today.getDate() - 6)
  else if (p === '30d') from.setDate(today.getDate() - 29)
  else if (p === 'month') from = new Date(today.getFullYear(), today.getMonth(), 1)
  fromDate.value = isoDay(from)
  toDate.value = isoDay(today)
}
function onCustomDate() { preset.value = 'custom' }

// ---------- Data ----------
const loading = ref(false)
const operator = ref<OperatorStatsRead | null>(null)
const timeseries = ref<OperatorTimeseriesRead | null>(null)
const activity = ref<OperatorActivityRead | null>(null)

async function loadAll() {
  if (!fromDate.value || !toDate.value || !operatorId.value) return
  loading.value = true
  try {
    const [lb, ts, act] = await Promise.all([
      adminApi.analytics.leaderboard({
        from: fromDate.value, to: toDate.value, operator_id: operatorId.value,
      }),
      adminApi.analytics.timeseries(operatorId.value, {
        from: fromDate.value, to: toDate.value,
      }),
      adminApi.analytics.activity(operatorId.value, {
        from: fromDate.value, to: toDate.value, limit: 30,
      }),
    ])
    operator.value = lb.items[0] || null
    timeseries.value = ts
    activity.value = act
  } catch {
    toast.error("Ma'lumotlarni yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

// ---------- Formatters ----------
function fmtMoney(v: string | number): string {
  return (Number(v) || 0).toLocaleString('uz-UZ')
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

// ---------- Charts ----------
const isDark = computed(() => theme.isDark)
const labelsForChart = computed(() => timeseries.value?.lead_activities_total.map(p => p.date.slice(5)) || [])

function dataset(label: string, color: string, points: number[]) {
  return {
    label, data: points, borderColor: color, backgroundColor: color + '22',
    borderWidth: 2, pointRadius: 2, pointHoverRadius: 4, tension: 0.3, fill: true,
  }
}

const conversionChart = computed(() => {
  if (!timeseries.value) return { labels: [], datasets: [] }
  return {
    labels: labelsForChart.value,
    datasets: [
      dataset('Lead harakatlari', '#6366f1', timeseries.value.lead_activities_total.map(p => p.value)),
      dataset('Konversiya', '#10b981', timeseries.value.lead_converts.map(p => p.value)),
      dataset('Abituriyent', '#f59e0b', timeseries.value.applicants_registered.map(p => p.value)),
    ],
  }
})

const contractsChart = computed(() => {
  if (!timeseries.value) return { labels: [], datasets: [] }
  return {
    labels: labelsForChart.value,
    datasets: [
      dataset('Shartnoma yaratildi', '#0ea5e9', timeseries.value.contracts_created.map(p => p.value)),
      dataset('Imzolandi', '#22c55e', timeseries.value.contracts_signed.map(p => p.value)),
      dataset("To'lov tasdiqlandi", '#a855f7', timeseries.value.payments_confirmed.map(p => p.value)),
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
  loadAll()
})

watch([fromDate, toDate, operatorId], loadAll)
</script>

<template>
  <div>
    <PageHeader :title="operator?.full_name || 'Operator analitikasi'"
                :subtitle="operator
                  ? `${roleLabel(operator.role)} · ${fromDate} → ${toDate}`
                  : 'Tanlangan oraliq bo\'yicha tafsilot'"
                :crumbs="[{ label: 'Operatorlar analitikasi', to: `${panelPrefix}/operator-analytics` }]">
      <RouterLink :to="`${panelPrefix}/operator-analytics`"
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition">
        <ArrowLeft class="w-3 h-3" />
        Reytingga qaytish
      </RouterLink>
    </PageHeader>

    <!-- Date range bar -->
    <section class="card p-4 mb-5">
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex flex-wrap items-center gap-1">
          <button v-for="opt in PRESET_LABELS"
                  :key="opt.key"
                  type="button"
                  class="px-3 py-1.5 rounded-md text-xs font-medium transition"
                  :class="preset === opt.key
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
                  @click="applyPreset(opt.key)">
            {{ opt.label }}
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
                  @click="loadAll">
            <RefreshCcw class="w-3 h-3" :class="{ 'animate-spin': loading }" />
            Yangilash
          </button>
        </div>
      </div>
    </section>

    <!-- Loading skeleton -->
    <section v-if="loading && !operator" class="space-y-5">
      <Skeleton class="h-24" />
      <Skeleton class="h-64" />
    </section>

    <!-- Operator identity card -->
    <section v-else-if="operator" class="card p-5 mb-5">
      <div class="flex items-start gap-4">
        <div class="grid place-items-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-violet-500 text-white text-xl font-bold shadow-sm shrink-0">
          {{ (operator.full_name || operator.phone || '?').slice(0, 1) }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
            {{ operator.full_name || 'Ism kiritilmagan' }}
          </div>
          <div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            <span class="inline-flex items-center gap-1">
              <Phone class="w-3 h-3" />
              <span class="font-mono">{{ operator.phone || '—' }}</span>
            </span>
            <span class="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-semibold">
              {{ roleLabel(operator.role) }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- KPI tiles — action-based lead numbers, then downstream funnel -->
    <section v-if="operator" class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
      <StatCard label="Lead harakatlari" :value="operator.lead_activities_total" :icon="Inbox" tone="amber"
                :hint="`${operator.leads_actioned} uniq lead'da`" />
      <StatCard label="Lead konversiyasi" :value="operator.lead_converts"
                :icon="TrendingUp" tone="emerald"
                :hint="`${operator.lead_loses} yo'qotildi · ${operator.leads_open_assigned} ochiq`" />
      <StatCard label="Imzolangan shartnoma" :value="operator.contracts_signed"
                :icon="Award" tone="brand"
                :hint="`${operator.contracts_created} yaratildi · ${operator.contracts_cancelled} bekor`" />
      <StatCard :label="`To'lov (so'm)`"
                :value="fmtMoney(operator.payments_confirmed_amount)"
                :icon="CreditCard" tone="emerald"
                :hint="`${operator.payments_confirmed} ta to'lov tasdiqlandi`" />
    </section>

    <!-- Lead action breakdown — how the operator spent the lead work -->
    <section v-if="operator" class="card p-5 mb-5">
      <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
        <Inbox class="w-4 h-4 text-amber-500" />
        Lead bo'yicha ish taqsimoti
      </h3>
      <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 text-sm">
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Yaratdi</div>
          <div class="text-lg font-bold tabular-nums">{{ operator.lead_creates }}</div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Qo'ng'iroq</div>
          <div class="text-lg font-bold tabular-nums">{{ operator.lead_calls }}</div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Izoh</div>
          <div class="text-lg font-bold tabular-nums">{{ operator.lead_comments }}</div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Bosqich</div>
          <div class="text-lg font-bold tabular-nums">{{ operator.lead_stage_moves }}</div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Biriktirdi</div>
          <div class="text-lg font-bold tabular-nums">{{ operator.lead_assigns }}</div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Konversiya</div>
          <div class="text-lg font-bold tabular-nums text-emerald-700 dark:text-emerald-300">{{ operator.lead_converts }}</div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Yo'qotdi</div>
          <div class="text-lg font-bold tabular-nums text-rose-700 dark:text-rose-300">{{ operator.lead_loses }}</div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Qayta ochdi</div>
          <div class="text-lg font-bold tabular-nums">{{ operator.lead_reopens }}</div>
        </div>
      </div>
    </section>

    <!-- Charts -->
    <section v-if="operator" class="grid lg:grid-cols-2 gap-5 mb-5">
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <TrendingUp class="w-4 h-4 text-emerald-500" />
          Funnel: Lead → Abituriyent
        </h3>
        <div class="h-64">
          <Line v-if="timeseries" :data="conversionChart" :options="chartOpts" />
          <Skeleton v-else class="h-full" />
        </div>
      </div>
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <FileText class="w-4 h-4 text-brand-500" />
          Shartnoma va to'lovlar
        </h3>
        <div class="h-64">
          <Line v-if="timeseries" :data="contractsChart" :options="chartOpts" />
          <Skeleton v-else class="h-full" />
        </div>
      </div>
    </section>

    <!-- Conversion strip + activity -->
    <section v-if="operator" class="grid lg:grid-cols-2 gap-5">
      <div class="card p-5">
        <div class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <AlertTriangle v-if="operator.leads_actioned && !operator.contracts_signed"
                         class="w-3.5 h-3.5 text-amber-500" />
          Konversiya foizi
        </div>
        <div class="grid grid-cols-3 gap-3 text-sm">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Lead → Konversiya</div>
            <div class="text-2xl font-bold tabular-nums">
              {{ operator.leads_actioned
                 ? Math.round((operator.lead_converts / operator.leads_actioned) * 100)
                 : 0 }}%
            </div>
          </div>
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Ariza → Qabul</div>
            <div class="text-2xl font-bold tabular-nums">
              {{ operator.applications_reviewed
                 ? Math.round((operator.applications_accepted / operator.applications_reviewed) * 100)
                 : 0 }}%
            </div>
          </div>
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Shartnoma → Imzo</div>
            <div class="text-2xl font-bold tabular-nums">
              {{ operator.contracts_created
                 ? Math.round((operator.contracts_signed / operator.contracts_created) * 100)
                 : 0 }}%
            </div>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <div class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center justify-between gap-2">
          <span class="inline-flex items-center gap-2">
            <Activity class="w-3.5 h-3.5 text-sky-500" />
            Faollik (audit jurnali)
          </span>
          <span v-if="activity" class="text-[10px] text-slate-500 dark:text-slate-400 tabular-nums">
            {{ activity.total }} ta yozuv
          </span>
        </div>
        <div v-if="!activity">
          <Skeleton class="h-40" />
        </div>
        <div v-else-if="!activity.rows.length"
             class="text-xs text-slate-500 dark:text-slate-400 py-6 text-center">
          Tanlangan oraliqda faollik yo'q
        </div>
        <ul v-else class="space-y-1.5 max-h-80 overflow-y-auto pr-1">
          <li v-for="row in activity.rows" :key="row.action"
              class="flex items-center gap-3 text-sm">
            <div class="flex-1 min-w-0">
              <div class="text-slate-700 dark:text-slate-300 truncate">
                {{ tr(AUDIT_ACTIONS, row.action) }}
              </div>
              <div v-if="!AUDIT_ACTIONS[row.action]"
                   class="text-[10px] font-mono text-slate-400 truncate">
                {{ row.action }}
              </div>
            </div>
            <span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 tabular-nums shrink-0">
              {{ row.count }}
            </span>
          </li>
        </ul>
      </div>
    </section>

    <!-- Empty state when operator_id doesn't match anything in range -->
    <section v-else class="card p-10 text-center text-sm text-slate-500 dark:text-slate-400">
      Bu operator topilmadi yoki tanlangan oraliqda faoliyat ko'rsatmagan
    </section>
  </div>
</template>
