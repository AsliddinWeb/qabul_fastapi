<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Bar, Doughnut, Line } from 'vue-chartjs'
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale,
  BarElement, PointElement, LineElement, Filler,
} from 'chart.js'
import {
  Users, Award, XCircle, Target, TrendingUp, TrendingDown, Clock,
  ArrowRight, Activity,
} from 'lucide-vue-next'
import { leadsApi, type Lead } from '@/api/leads.api'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Filler)

const auth = useAuthStore()
const theme = useThemeStore()
const meId = computed(() => auth.user?.id || '')

const loading = ref(true)
const myLeads = ref<Lead[]>([])
const range = ref<'month' | 'quarter' | 'year'>('month')

onMounted(async () => {
  try {
    const r = await leadsApi.list({ assigned_to_id: meId.value, page: 1, size: 500 })
    myLeads.value = r.items || []
  } finally {
    loading.value = false
  }
})

// ---- Range cutoff ----
function rangeStart(): Date {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  if (range.value === 'month') {
    d.setDate(1)
  } else if (range.value === 'quarter') {
    const q = Math.floor(d.getMonth() / 3)
    d.setMonth(q * 3, 1)
  } else {
    d.setMonth(0, 1)
  }
  return d
}

const rangeLeads = computed(() => {
  const start = rangeStart().getTime()
  return myLeads.value.filter(l => new Date(l.created_at).getTime() >= start)
})

// Previous range (for trend deltas)
function prevRangeBounds(): [Date, Date] {
  const now = new Date()
  const end = rangeStart()
  const start = new Date(end)
  if (range.value === 'month') start.setMonth(start.getMonth() - 1)
  else if (range.value === 'quarter') start.setMonth(start.getMonth() - 3)
  else start.setFullYear(start.getFullYear() - 1)
  return [start, end]
}
const prevLeads = computed(() => {
  const [s, e] = prevRangeBounds()
  return myLeads.value.filter(l => {
    const t = new Date(l.created_at).getTime()
    return t >= s.getTime() && t < e.getTime()
  })
})

// ---- KPIs ----
const created     = computed(() => rangeLeads.value.length)
const won         = computed(() => rangeLeads.value.filter(l => l.status === 'won').length)
const lost        = computed(() => rangeLeads.value.filter(l => l.status === 'lost').length)
const openCount   = computed(() => rangeLeads.value.filter(l => l.status === 'open').length)
const conversion  = computed(() => {
  const closed = won.value + lost.value
  return closed ? Math.round((won.value / closed) * 100) : 0
})

const prevCreated    = computed(() => prevLeads.value.length)
const prevWon        = computed(() => prevLeads.value.filter(l => l.status === 'won').length)
const prevConversion = computed(() => {
  const w = prevLeads.value.filter(l => l.status === 'won').length
  const lo = prevLeads.value.filter(l => l.status === 'lost').length
  return (w + lo) ? Math.round((w / (w + lo)) * 100) : 0
})

function pctDelta(curr: number, prev: number): number {
  if (prev === 0) return curr > 0 ? 100 : 0
  return Math.round(((curr - prev) / prev) * 100)
}
const dCreated = computed(() => pctDelta(created.value, prevCreated.value))
const dWon     = computed(() => pctDelta(won.value, prevWon.value))
const dConv    = computed(() => conversion.value - prevConversion.value)

// ---- Source breakdown ----
const bySource = computed(() => {
  const buckets: Record<string, { name: string; total: number; won: number; lost: number; open: number }> = {}
  for (const l of rangeLeads.value) {
    const key = l.source_id || '__none__'
    const name = l.source_name || 'Manba ko\'rsatilmagan'
    if (!buckets[key]) buckets[key] = { name, total: 0, won: 0, lost: 0, open: 0 }
    buckets[key].total++
    if (l.status === 'won') buckets[key].won++
    else if (l.status === 'lost') buckets[key].lost++
    else buckets[key].open++
  }
  return Object.values(buckets)
    .map(b => ({
      ...b,
      conv: (b.won + b.lost) ? Math.round((b.won / (b.won + b.lost)) * 100) : 0,
    }))
    .sort((a, b) => b.total - a.total)
})

// ---- Stage distribution (open leads only) ----
const byStage = computed(() => {
  const buckets: Record<string, { name: string; color: string | null; count: number }> = {}
  for (const l of rangeLeads.value) {
    if (l.status !== 'open') continue
    const key = l.stage_id
    const name = l.stage_name || '—'
    if (!buckets[key]) buckets[key] = { name, color: l.stage_color, count: 0 }
    buckets[key].count++
  }
  return Object.values(buckets).sort((a, b) => b.count - a.count)
})

// ---- Trend chart (12-month created/won) ----
const txt = computed(() => theme.isDark ? '#cbd5e1' : '#64748b')
const grid = computed(() => theme.isDark ? 'rgba(148,163,184,0.10)' : 'rgba(100,116,139,0.10)')
const brand500 = '#3f56ef'
const brand200 = '#b8ccff'
const emerald  = '#10b981'

const monthlyTrend = computed(() => {
  const buckets: Record<string, { total: number; won: number }> = {}
  const now = new Date()
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    buckets[key] = { total: 0, won: 0 }
  }
  for (const l of myLeads.value) {
    const d = new Date(l.created_at)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    if (key in buckets) {
      buckets[key].total++
      if (l.status === 'won') buckets[key].won++
    }
  }
  return Object.entries(buckets).map(([k, v]) => ({ month: k, ...v }))
})

const MONTHS = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']
const trendChart = computed(() => ({
  labels: monthlyTrend.value.map(b => MONTHS[+b.month.split('-')[1] - 1]),
  datasets: [
    {
      label: 'Yaratilgan',
      data: monthlyTrend.value.map(b => b.total),
      backgroundColor: brand200,
      borderRadius: 6,
    },
    {
      label: 'Yutilgan',
      data: monthlyTrend.value.map(b => b.won),
      backgroundColor: brand500,
      borderRadius: 6,
    },
  ],
}))
const trendOpts = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' as const, labels: { color: txt.value, padding: 12, usePointStyle: true, pointStyle: 'circle' as const, font: { size: 11 } } },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { ticks: { color: txt.value, font: { size: 11 } }, grid: { display: false } },
    y: { ticks: { color: txt.value, precision: 0 }, grid: { color: grid.value } },
  },
}))

// ---- Status doughnut ----
const statusDoughnut = computed(() => ({
  labels: ['Faol', 'Yutilgan', "Yo'qotilgan"],
  datasets: [{
    data: [openCount.value, won.value, lost.value],
    backgroundColor: [brand500, emerald, '#f43f5e'],
    borderWidth: 0,
  }],
}))
const doughnutOpts = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '72%',
  plugins: { legend: { display: false } },
}))

// ---- Average response time (created → first activity by me, in hours) ----
const avgResponseHours = ref<number | null>(null)
async function loadResponseTime() {
  // Sample first 30 leads for activities
  const sample = myLeads.value.slice(0, 30)
  let totalMs = 0
  let count = 0
  for (const l of sample) {
    try {
      const acts = await leadsApi.activities(l.id)
      const myActs = acts.filter(a => a.user_id === meId.value && a.action !== 'create')
      if (myActs.length === 0) continue
      const first = myActs.reduce((min, a) => new Date(a.created_at).getTime() < new Date(min.created_at).getTime() ? a : min, myActs[0])
      const diff = new Date(first.created_at).getTime() - new Date(l.created_at).getTime()
      if (diff > 0) { totalMs += diff; count++ }
    } catch { /* ignore */ }
  }
  avgResponseHours.value = count ? Math.round((totalMs / count) / 3_600_000 * 10) / 10 : null
}

onMounted(async () => {
  // Compute response time after main data loads
  setTimeout(() => loadResponseTime(), 100)
})

const rangeLabel = computed(() => {
  if (range.value === 'month') return 'Bu oy'
  if (range.value === 'quarter') return 'Bu kvartal'
  return 'Bu yil'
})
const rangeShort = computed(() => {
  if (range.value === 'month') return "vs o'tgan oy"
  if (range.value === 'quarter') return "vs o'tgan kvartal"
  return "vs o'tgan yil"
})
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Mening statistikam"
      :subtitle="`Sizning unumdorligingiz va konversiya tahlili — ${rangeLabel}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/operator' }, { label: 'CRM' }]"
    >
      <!-- Range pill -->
      <div class="inline-flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 text-xs font-medium">
        <button class="px-3 py-1.5 rounded-md transition-colors"
                :class="range === 'month' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                @click="range = 'month'">Oy</button>
        <button class="px-3 py-1.5 rounded-md transition-colors"
                :class="range === 'quarter' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                @click="range = 'quarter'">Kvartal</button>
        <button class="px-3 py-1.5 rounded-md transition-colors"
                :class="range === 'year' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                @click="range = 'year'">Yil</button>
      </div>
    </PageHeader>

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else>
      <!-- KPI cards -->
      <section class="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Yaratilgan"
          :value="created"
          :icon="Users"
          tone="brand"
          :trend="dCreated"
          :trend-hint="rangeShort"
        />
        <StatCard
          label="Yutilgan"
          :value="won"
          :icon="Award"
          tone="emerald"
          :trend="dWon"
          :trend-hint="rangeShort"
        />
        <StatCard
          label="Yo'qotilgan"
          :value="lost"
          :icon="XCircle"
          tone="rose"
          :hint="`Ochiq: ${openCount}`"
        />
        <StatCard
          label="Konversiya"
          :value="`${conversion}%`"
          :icon="Target"
          tone="violet"
          :trend="dConv"
          :trend-hint="rangeShort + ' (pp)'"
        />
      </section>

      <!-- Hero gradient + Doughnut -->
      <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Gradient hero -->
        <div class="relative overflow-hidden rounded-2xl p-5 text-white shadow-card md:col-span-2"
             style="background: linear-gradient(135deg, #3f56ef 0%, #5b6cf5 50%, #8b5cf6 100%);">
          <div class="absolute inset-0 opacity-30"
               style="background-image: radial-gradient(circle at 20% 100%, rgba(255,255,255,0.2) 0%, transparent 50%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.15) 0%, transparent 60%);"></div>
          <div class="relative flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-wider opacity-80 mb-1">Konversiya</div>
              <div class="text-4xl font-bold tracking-tight tabular-nums">{{ conversion }}%</div>
              <div class="mt-2 inline-flex items-center gap-2 text-sm">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-white/20 backdrop-blur">
                  <component :is="dConv >= 0 ? TrendingUp : TrendingDown" class="w-3 h-3" />
                  {{ dConv >= 0 ? '+' : '' }}{{ dConv }} pp
                </span>
                <span class="opacity-80 text-xs">{{ rangeShort }}</span>
              </div>
              <div class="mt-4 grid grid-cols-3 gap-3 text-xs opacity-95">
                <div>
                  <div class="text-[10px] uppercase tracking-wider opacity-70">Yaratilgan</div>
                  <div class="text-base font-semibold tabular-nums">{{ created }}</div>
                </div>
                <div>
                  <div class="text-[10px] uppercase tracking-wider opacity-70">Yutilgan</div>
                  <div class="text-base font-semibold tabular-nums">{{ won }}</div>
                </div>
                <div>
                  <div class="text-[10px] uppercase tracking-wider opacity-70">O'rtacha javob</div>
                  <div class="text-base font-semibold tabular-nums">
                    {{ avgResponseHours == null ? '—' : `${avgResponseHours}h` }}
                  </div>
                </div>
              </div>
            </div>
            <div class="grid place-items-center w-14 h-14 rounded-2xl bg-white/15 backdrop-blur shrink-0">
              <Target class="w-6 h-6" />
            </div>
          </div>
        </div>

        <!-- Status doughnut -->
        <div class="card p-5">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-4">Holat taqsimoti</h2>
          <div class="relative">
            <div class="h-44">
              <Doughnut :data="statusDoughnut" :options="doughnutOpts" />
            </div>
            <div class="absolute inset-0 grid place-items-center pointer-events-none">
              <div class="text-center">
                <div class="text-2xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{{ created }}</div>
                <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">jami</div>
              </div>
            </div>
          </div>
          <ul class="mt-4 space-y-1.5 text-xs">
            <li class="flex items-center justify-between">
              <span class="inline-flex items-center gap-2"><span class="w-2 h-2 rounded-full" :style="{ backgroundColor: brand500 }"></span>Faol</span>
              <strong class="tabular-nums">{{ openCount }}</strong>
            </li>
            <li class="flex items-center justify-between">
              <span class="inline-flex items-center gap-2"><span class="w-2 h-2 rounded-full" :style="{ backgroundColor: emerald }"></span>Yutilgan</span>
              <strong class="tabular-nums">{{ won }}</strong>
            </li>
            <li class="flex items-center justify-between">
              <span class="inline-flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-rose-500"></span>Yo'qotilgan</span>
              <strong class="tabular-nums">{{ lost }}</strong>
            </li>
          </ul>
        </div>
      </section>

      <!-- 12-month bar chart -->
      <section class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">12 oylik trend</h2>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Sizning oylik unumdorligingiz</p>
          </div>
        </div>
        <div class="h-72">
          <Bar :data="trendChart" :options="trendOpts" />
        </div>
      </section>

      <!-- Source breakdown + stage distribution -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <span class="grid place-items-center w-7 h-7 rounded-lg bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
                <Activity class="w-3.5 h-3.5" />
              </span>
              Manba bo'yicha sinish
            </h2>
            <span class="text-xs text-slate-500 dark:text-slate-400">{{ rangeLabel }}</span>
          </div>
          <ul v-if="bySource.length" class="space-y-3">
            <li v-for="row in bySource" :key="row.name">
              <div class="flex items-baseline justify-between mb-1">
                <span class="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{{ row.name }}</span>
                <span class="text-xs text-slate-500 dark:text-slate-400 tabular-nums shrink-0 ml-2">
                  <strong class="text-slate-900 dark:text-slate-100">{{ row.won }}</strong> / {{ row.total }}
                  <span class="ml-1.5 font-semibold"
                        :class="row.conv >= 50
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : row.conv >= 20
                            ? 'text-amber-600 dark:text-amber-400'
                            : 'text-rose-600 dark:text-rose-400'">
                    {{ row.conv }}%
                  </span>
                </span>
              </div>
              <div class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div class="h-full rounded-full transition-all"
                     :class="row.conv >= 50 ? 'bg-emerald-500' : row.conv >= 20 ? 'bg-amber-500' : 'bg-rose-500'"
                     :style="{ width: Math.max(row.conv, 1) + '%' }"></div>
              </div>
            </li>
          </ul>
          <div v-else class="py-12 text-center">
            <div class="inline-grid place-items-center w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500 mb-3">
              <Activity class="w-5 h-5" />
            </div>
            <div class="text-sm text-slate-500 dark:text-slate-400">{{ rangeLabel }} ichida lead yo'q</div>
          </div>
        </div>

        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <span class="grid place-items-center w-7 h-7 rounded-lg bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-300">
                <ArrowRight class="w-3.5 h-3.5" />
              </span>
              Aktiv lead'lar — bosqich bo'yicha
            </h2>
          </div>
          <ul v-if="byStage.length" class="space-y-3">
            <li v-for="row in byStage" :key="row.name" class="flex items-center gap-3">
              <span class="w-3 h-3 rounded-full ring-2 ring-white dark:ring-slate-900 shrink-0"
                    :style="{ backgroundColor: row.color || '#94a3b8' }"></span>
              <span class="text-sm font-medium text-slate-700 dark:text-slate-300 flex-1 truncate">{{ row.name }}</span>
              <div class="w-32 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden shrink-0">
                <div class="h-full rounded-full"
                     :style="{
                       width: Math.max(Math.round(row.count / openCount * 100), 4) + '%',
                       backgroundColor: row.color || '#94a3b8',
                     }"></div>
              </div>
              <span class="text-sm font-bold text-slate-900 dark:text-slate-100 tabular-nums w-8 text-right shrink-0">{{ row.count }}</span>
            </li>
          </ul>
          <div v-else class="py-12 text-center">
            <div class="inline-grid place-items-center w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500 mb-3">
              <ArrowRight class="w-5 h-5" />
            </div>
            <div class="text-sm text-slate-500 dark:text-slate-400">Aktiv lead'lar yo'q</div>
          </div>
        </div>
      </section>

      <!-- Response time card -->
      <section class="card p-5">
        <div class="flex items-center gap-4">
          <span class="grid place-items-center w-12 h-12 rounded-xl bg-sky-100 text-sky-600 dark:bg-sky-500/20 dark:text-sky-300 shrink-0">
            <Clock class="w-5 h-5" />
          </span>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">O'rtacha javob vaqti</div>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Lead yaratilgandan birinchi harakatingizgacha o'tgan vaqt
            </p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold tabular-nums"
                 :class="avgResponseHours == null
                   ? 'text-slate-400'
                   : avgResponseHours <= 1
                     ? 'text-emerald-600 dark:text-emerald-400'
                     : avgResponseHours <= 6
                       ? 'text-amber-600 dark:text-amber-400'
                       : 'text-rose-600 dark:text-rose-400'">
              {{ avgResponseHours == null ? 'Yuklanmoqda...' : `${avgResponseHours} soat` }}
            </div>
            <div class="text-[11px] text-slate-500 dark:text-slate-400">oxirgi 30 lead namunasidan</div>
          </div>
        </div>
      </section>

      <!-- Line activity unused for now -->
      <Line v-show="false" :data="{ labels: [], datasets: [] }" :options="{}" />
    </template>
  </div>
</template>
