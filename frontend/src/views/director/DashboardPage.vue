<script setup lang="ts">
/**
 * Director Dashboard — read-only overview of the admission campaign.
 *
 * Bird's-eye view a director uses to track funnel health without having
 * to drill into the operator analytics page. Composed of six sections:
 *
 *   1. Hero strip with date-range presets (default: this month)
 *   2. KPI strip — 6 cards with vs-previous-period deltas
 *   3. 12-month application trend (stacked bar by status)
 *   4. Two-up: lead funnel doughnut + application status doughnut
 *   5. Top operators leaderboard (top 5 by accepted applications)
 *   6. Two-up: payments summary + top debtors
 *
 * Mobile-first: every grid collapses to one column on phones, fans out
 * to 2/3/5 columns at sm/lg/xl breakpoints. Charts maintainAspectRatio
 * = false so they reflow inside fixed-height parents.
 *
 * Permissions: director role carries reports.view + reports.financial
 * + applications.list / leads.list / contracts.read / payments.read,
 * which covers every endpoint touched here.
 */
import { computed, onMounted, ref } from 'vue'
import { Bar, Doughnut, Line } from 'vue-chartjs'
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale,
  BarElement, PointElement, LineElement, Filler,
} from 'chart.js'
import {
  Users, ClipboardList, FileCheck, FileText, CreditCard, TrendingUp,
  TrendingDown, Target, Trophy, AlertTriangle, Activity, Wallet,
  ArrowRight, Sparkles, Crown,
} from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

import { staffApi } from '@/api/staff.api'
import { adminApi } from '@/api/admin.api'
import { paymentsApi } from '@/api/payments.api'
import { leadsApi } from '@/api/leads.api'
import { useThemeStore } from '@/stores/theme'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Filler)

const theme = useThemeStore()
const loading = ref(true)
const loadError = ref<string | null>(null)

// ---- Date range (drives the operator leaderboard only — the global
//      "total" KPIs are cumulative and not range-bound) ----
type RangeKey = 'month' | 'quarter' | 'year'
const range = ref<RangeKey>('month')

function rangeStart(): Date {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  if (range.value === 'month') d.setDate(1)
  else if (range.value === 'quarter') { const q = Math.floor(d.getMonth() / 3); d.setMonth(q * 3, 1) }
  else d.setMonth(0, 1)
  return d
}
function prevRangeBounds(): [Date, Date] {
  const end = rangeStart()
  const start = new Date(end)
  if (range.value === 'month') start.setMonth(start.getMonth() - 1)
  else if (range.value === 'quarter') start.setMonth(start.getMonth() - 3)
  else start.setFullYear(start.getFullYear() - 1)
  return [start, end]
}
const rangeLabel = computed(() => range.value === 'month' ? 'Bu oy' : range.value === 'quarter' ? 'Bu kvartal' : 'Bu yil')
const rangeShort = computed(() => range.value === 'month' ? "vs o'tgan oy" : range.value === 'quarter' ? "vs o'tgan kvartal" : "vs o'tgan yil")

// ---- Reactive data ----
const apps = ref({ topshirildi: 0, korib_chiqilmoqda: 0, qabul_qilindi: 0, rad_etildi: 0, total: 0 })
const applicantsTotal = ref(0)
const contractsSigned = ref(0)
const leadStats = ref<{ total: number; open: number; won: number; lost: number; conversion_rate: number; by_stage: any[] } | null>(null)
const leadBreakdown = ref<{ by_source: Array<any>; by_operator: Array<any> } | null>(null)
const monthlyTrend = ref<Array<{ month: string; topshirildi: number; korib_chiqilmoqda: number; qabul_qilindi: number; rad_etildi: number; total: number }>>([])
const paymentsDash = ref<any>(null)
const leaderboard = ref<any[]>([])
const leaderboardPrev = ref<any[]>([])

const periodAppsTotal = ref(0)
const periodAppsAccepted = ref(0)
const periodAppsTotalPrev = ref(0)
const periodAppsAcceptedPrev = ref(0)

async function appsInRangeTotal(status: string | undefined, from: Date, to: Date) {
  try {
    const r = await staffApi.applications.list({
      status: status as any,
      created_from: from.toISOString(),
      created_to: to.toISOString(),
      page: 1, size: 1,
    } as any)
    return r.total
  } catch { return 0 }
}

async function loadAll() {
  loading.value = true
  loadError.value = null
  try {
    const [from, to] = [rangeStart(), new Date()]
    const [prevFrom, prevTo] = prevRangeBounds()
    const fromS = from.toISOString().slice(0, 10)
    const toS = to.toISOString().slice(0, 10)
    const prevFromS = prevFrom.toISOString().slice(0, 10)
    const prevToS = prevTo.toISOString().slice(0, 10)

    const [
      stats, applicants, trend, lstats, lbreak, pays, board, prevBoard,
      contracts, periodAll, periodAcc, periodAllPrev, periodAccPrev,
    ] = await Promise.all([
      adminApi.applications.stats().catch(() => ({} as any)),
      staffApi.applicants.list({ page: 1, size: 1 }).then((r: any) => r.total).catch(() => 0),
      adminApi.applications.trend(12).catch(() => []),
      leadsApi.stats().catch(() => null),
      leadsApi.breakdown().catch(() => ({ by_source: [], by_operator: [] }) as any),
      paymentsApi.dashboard().catch(() => null),
      adminApi.analytics.leaderboard({ from: fromS, to: toS }).catch(() => ({ items: [] }) as any),
      adminApi.analytics.leaderboard({ from: prevFromS, to: prevToS }).catch(() => ({ items: [] }) as any),
      adminApi.contracts.list({ status: 'signed', size: 1 }).then((r: any) => r.total).catch(() => 0),
      appsInRangeTotal(undefined, from, to),
      appsInRangeTotal('qabul_qilindi', from, to),
      appsInRangeTotal(undefined, prevFrom, prevTo),
      appsInRangeTotal('qabul_qilindi', prevFrom, prevTo),
    ])

    apps.value = {
      topshirildi: (stats as any).topshirildi || 0,
      korib_chiqilmoqda: (stats as any).korib_chiqilmoqda || 0,
      qabul_qilindi: (stats as any).qabul_qilindi || 0,
      rad_etildi: (stats as any).rad_etildi || 0,
      total: (stats as any).total || 0,
    }
    applicantsTotal.value = applicants
    monthlyTrend.value = trend
    leadStats.value = lstats
    leadBreakdown.value = lbreak
    paymentsDash.value = pays
    leaderboard.value = (board as any)?.items || []
    leaderboardPrev.value = (prevBoard as any)?.items || []
    contractsSigned.value = contracts
    periodAppsTotal.value = periodAll
    periodAppsAccepted.value = periodAcc
    periodAppsTotalPrev.value = periodAllPrev
    periodAppsAcceptedPrev.value = periodAccPrev
  } catch (e: any) {
    loadError.value = e?.response?.data?.detail || "Yuklab bo'lmadi"
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

function pctDelta(curr: number, prev: number): number {
  if (prev === 0) return curr > 0 ? 100 : 0
  return Math.round(((curr - prev) / prev) * 100)
}

// ---- KPI derived values ----
const acceptedRate = computed(() => {
  const denom = apps.value.korib_chiqilmoqda + apps.value.qabul_qilindi + apps.value.rad_etildi
  return denom ? Math.round((apps.value.qabul_qilindi / denom) * 100) : 0
})
const dAppsTotal = computed(() => pctDelta(periodAppsTotal.value, periodAppsTotalPrev.value))
const dAccepted = computed(() => pctDelta(periodAppsAccepted.value, periodAppsAcceptedPrev.value))
const periodSignedDelta = computed(() => {
  const c = leaderboard.value.reduce((s: number, x: any) => s + (x.contracts_signed || 0), 0)
  const p = leaderboardPrev.value.reduce((s: number, x: any) => s + (x.contracts_signed || 0), 0)
  return { curr: c, delta: pctDelta(c, p) }
})

// ---- Charts ----
const txt = computed(() => theme.isDark ? '#cbd5e1' : '#64748b')
const grid = computed(() => theme.isDark ? 'rgba(148,163,184,0.10)' : 'rgba(100,116,139,0.10)')
const brand500 = '#3f56ef'
const emerald  = '#10b981'
const amber    = '#f59e0b'
const rose     = '#f43f5e'
const sky      = '#0ea5e9'

const MONTHS = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']
function monthShort(iso: string): string {
  const [, m] = iso.split('-')
  return MONTHS[Math.max(0, Math.min(11, Number(m) - 1))]
}

const trendChart = computed(() => ({
  labels: monthlyTrend.value.map((b: any) => monthShort(b.month)),
  datasets: [
    { label: 'Topshirildi',        data: monthlyTrend.value.map((b: any) => b.topshirildi),        backgroundColor: amber, borderRadius: 4, stack: 'a' },
    { label: "Ko'rib chiqilmoqda", data: monthlyTrend.value.map((b: any) => b.korib_chiqilmoqda), backgroundColor: sky,    borderRadius: 4, stack: 'a' },
    { label: 'Qabul qilindi',      data: monthlyTrend.value.map((b: any) => b.qabul_qilindi),      backgroundColor: emerald, borderRadius: 4, stack: 'a' },
    { label: 'Rad etildi',         data: monthlyTrend.value.map((b: any) => b.rad_etildi),         backgroundColor: rose,   borderRadius: 4, stack: 'a' },
  ],
}))
const trendOpts = computed(() => ({
  responsive: true, maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' as const, labels: { color: txt.value, padding: 12, usePointStyle: true, pointStyle: 'circle' as const, font: { size: 11 } } },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { ticks: { color: txt.value, font: { size: 11 } }, grid: { display: false }, stacked: true },
    y: { ticks: { color: txt.value, precision: 0 }, grid: { color: grid.value }, stacked: true },
  },
}))

const appsDoughnut = computed(() => ({
  labels: ['Topshirildi', "Ko'rilmoqda", 'Qabul', 'Rad'],
  datasets: [{
    data: [apps.value.topshirildi, apps.value.korib_chiqilmoqda, apps.value.qabul_qilindi, apps.value.rad_etildi],
    backgroundColor: [amber, sky, emerald, rose],
    borderWidth: 0,
  }],
}))
const leadsDoughnut = computed(() => ({
  labels: ['Faol', 'Konversiya', "Yo'qotilgan"],
  datasets: [{
    data: [leadStats.value?.open || 0, leadStats.value?.won || 0, leadStats.value?.lost || 0],
    backgroundColor: [brand500, emerald, rose],
    borderWidth: 0,
  }],
}))
const doughnutOpts = computed(() => ({
  responsive: true, maintainAspectRatio: false, cutout: '70%',
  plugins: {
    legend: { position: 'bottom' as const, labels: { color: txt.value, padding: 10, usePointStyle: true, pointStyle: 'circle' as const, font: { size: 11 } } },
  },
}))

// Payment monthly sparkline
const paymentSparkData = computed(() => {
  const rows = (paymentsDash.value?.monthly_trend || []) as Array<{ month: string; count: number; sum: string }>
  return {
    labels: rows.map(r => monthShort(r.month)),
    datasets: [{
      data: rows.map(r => Number(r.sum) || 0),
      borderColor: brand500,
      backgroundColor: 'rgba(63, 86, 239, 0.12)',
      tension: 0.35,
      fill: true,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointHoverBackgroundColor: brand500,
    }],
  }
})
const paymentSparkOpts = computed(() => ({
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { intersect: false, mode: 'index' as const } },
  scales: {
    x: { ticks: { color: txt.value, font: { size: 10 } }, grid: { display: false } },
    y: { ticks: { color: txt.value, callback: (v: any) => fmtCompact(Number(v)) }, grid: { color: grid.value } },
  },
}))

// Top leaderboard (top 5 by accepted)
const topOperators = computed(() => {
  return [...leaderboard.value]
    .sort((a, b) => (b.applications_accepted || 0) - (a.applications_accepted || 0))
    .slice(0, 5)
})

// Source breakdown — top 6 sources by total
const topSources = computed(() => {
  const rows = leadBreakdown.value?.by_source || []
  return [...rows]
    .sort((a, b) => (b.total || 0) - (a.total || 0))
    .slice(0, 6)
})

// ---- Helpers ----
function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '0'
  return Math.round(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}
function fmtCompact(n: number): string {
  if (!Number.isFinite(n)) return '0'
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return String(Math.round(n))
}
function initials(name: string | null | undefined): string {
  if (!name) return '?'
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]?.toUpperCase() || '').join('') || '?'
}
function avatarColor(id: string): string {
  const palette = ['from-brand-500 to-violet-500', 'from-emerald-500 to-teal-500', 'from-amber-500 to-orange-500', 'from-rose-500 to-pink-500', 'from-sky-500 to-cyan-500']
  let h = 0
  for (let i = 0; i < id.length; i++) h = ((h << 5) - h + id.charCodeAt(i)) | 0
  return palette[Math.abs(h) % palette.length]
}
function opConvRate(o: any): number {
  const tot = (o.applications_accepted || 0) + (o.applications_rejected || 0)
  return tot ? Math.round((o.applications_accepted / tot) * 100) : 0
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Direktor paneli"
      :subtitle="`Qabul kampaniyasining umumiy ko'rsatkichlari — ${rangeLabel}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/director' }]"
    >
      <!-- Range pill — mobile: full width below header; desktop: in slot -->
      <div class="inline-flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 text-xs font-medium shrink-0">
        <button class="px-3 py-1.5 rounded-md transition-colors"
                :class="range === 'month' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                @click="range = 'month'; loadAll()">Oy</button>
        <button class="px-3 py-1.5 rounded-md transition-colors"
                :class="range === 'quarter' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                @click="range = 'quarter'; loadAll()">Kvartal</button>
        <button class="px-3 py-1.5 rounded-md transition-colors"
                :class="range === 'year' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                @click="range = 'year'; loadAll()">Yil</button>
      </div>
    </PageHeader>

    <Skeleton v-if="loading" type="dashboard" />

    <div v-else-if="loadError"
         class="card p-6 flex items-start gap-3 ring-1 ring-rose-200 dark:ring-rose-700/40 bg-rose-50/40 dark:bg-rose-500/10">
      <AlertTriangle class="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
      <div>
        <div class="font-medium text-rose-700 dark:text-rose-300">Statistikani yuklab bo'lmadi</div>
        <div class="text-xs text-rose-600 dark:text-rose-400 mt-1">{{ loadError }}</div>
      </div>
    </div>

    <template v-else>
      <!-- ===== HERO GRADIENT — period summary ===== -->
      <section class="relative overflow-hidden rounded-2xl p-5 sm:p-6 text-white shadow-card"
               style="background: linear-gradient(135deg, #3f56ef 0%, #5b6cf5 50%, #8b5cf6 100%);">
        <div class="absolute inset-0 opacity-30 pointer-events-none"
             style="background-image: radial-gradient(circle at 20% 100%, rgba(255,255,255,0.2) 0%, transparent 50%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.18) 0%, transparent 60%);"></div>
        <div class="relative flex flex-wrap items-start gap-5">
          <div class="flex-1 min-w-0">
            <div class="text-xs uppercase tracking-wider opacity-80 mb-1 inline-flex items-center gap-1.5">
              <Sparkles class="w-3 h-3" /> {{ rangeLabel }}
            </div>
            <div class="text-4xl sm:text-5xl font-bold tabular-nums tracking-tight">
              {{ periodAppsTotal }}
            </div>
            <div class="text-sm opacity-90 mt-1">yangi ariza topshirildi</div>
            <div class="mt-3 inline-flex items-center gap-2 text-xs">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-semibold bg-white/20 backdrop-blur">
                <component :is="dAppsTotal >= 0 ? TrendingUp : TrendingDown" class="w-3 h-3" />
                {{ dAppsTotal >= 0 ? '+' : '' }}{{ dAppsTotal }}%
              </span>
              <span class="opacity-80">{{ rangeShort }}</span>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-4 sm:gap-6 shrink-0">
            <div>
              <div class="text-[10px] uppercase tracking-wider opacity-70">Qabul qilindi</div>
              <div class="text-2xl font-bold tabular-nums mt-0.5">{{ periodAppsAccepted }}</div>
              <div class="text-[11px] opacity-80">
                <component :is="dAccepted >= 0 ? TrendingUp : TrendingDown" class="w-2.5 h-2.5 inline" />
                {{ dAccepted >= 0 ? '+' : '' }}{{ dAccepted }}%
              </div>
            </div>
            <div>
              <div class="text-[10px] uppercase tracking-wider opacity-70">Imzolangan</div>
              <div class="text-2xl font-bold tabular-nums mt-0.5">{{ periodSignedDelta.curr }}</div>
              <div class="text-[11px] opacity-80">
                <component :is="periodSignedDelta.delta >= 0 ? TrendingUp : TrendingDown" class="w-2.5 h-2.5 inline" />
                {{ periodSignedDelta.delta >= 0 ? '+' : '' }}{{ periodSignedDelta.delta }}%
              </div>
            </div>
            <div>
              <div class="text-[10px] uppercase tracking-wider opacity-70">To'lov</div>
              <div class="text-2xl font-bold tabular-nums mt-0.5">{{ fmtCompact(Number(paymentsDash?.month_sum || 0)) }}</div>
              <div class="text-[11px] opacity-80">{{ paymentsDash?.month_count || 0 }} ta</div>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== KPI STRIP — cumulative ===== -->
      <section class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3 sm:gap-4">
        <StatCard label="Jami abituriyentlar" :value="applicantsTotal" :icon="Users" tone="brand" />
        <StatCard label="Jami arizalar" :value="apps.total" :icon="ClipboardList" tone="sky" />
        <StatCard label="Qabul qilindi" :value="apps.qabul_qilindi" :icon="FileCheck" tone="emerald"
                  :hint="`Konversiya: ${acceptedRate}%`" />
        <StatCard label="Imzolangan shartnoma" :value="contractsSigned" :icon="FileText" tone="violet" />
        <StatCard label="Jami leadlar" :value="leadStats?.total || 0" :icon="Activity" tone="amber"
                  :hint="`Faol: ${leadStats?.open || 0}`" />
        <StatCard label="Lead konversiya" :value="`${Math.round(leadStats?.conversion_rate || 0)}%`" :icon="Target" tone="rose" />
      </section>

      <!-- ===== TREND CHART — 12 month stacked bar ===== -->
      <section class="card p-4 sm:p-6">
        <div class="flex items-start justify-between mb-4 gap-2 flex-wrap">
          <div>
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">Arizalar trendi (12 oy)</h2>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Holat bo'yicha taqsimlangan</p>
          </div>
          <RouterLink to="/director/applications"
                      class="text-xs font-semibold text-brand-700 dark:text-brand-300 hover:text-brand-800 inline-flex items-center gap-1">
            Arizalar ro'yxati <ArrowRight class="w-3 h-3" />
          </RouterLink>
        </div>
        <div class="h-56 sm:h-72">
          <Bar :data="trendChart" :options="trendOpts" />
        </div>
      </section>

      <!-- ===== TWO-UP: Application + Lead doughnuts ===== -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
        <div class="card p-4 sm:p-6">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-4">Arizalar holati</h2>
          <div v-if="apps.total === 0" class="py-12 text-center text-sm text-slate-500 dark:text-slate-400">Ma'lumot yo'q</div>
          <div v-else class="relative">
            <div class="h-44 sm:h-52">
              <Doughnut :data="appsDoughnut" :options="doughnutOpts" />
            </div>
            <div class="absolute top-0 left-0 right-0 h-44 sm:h-52 grid place-items-center pointer-events-none -mt-6">
              <div class="text-center">
                <div class="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{{ apps.total }}</div>
                <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">jami</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card p-4 sm:p-6">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-4">Lead voronkasi</h2>
          <div v-if="!leadStats || leadStats.total === 0" class="py-12 text-center text-sm text-slate-500 dark:text-slate-400">Ma'lumot yo'q</div>
          <div v-else class="relative">
            <div class="h-44 sm:h-52">
              <Doughnut :data="leadsDoughnut" :options="doughnutOpts" />
            </div>
            <div class="absolute top-0 left-0 right-0 h-44 sm:h-52 grid place-items-center pointer-events-none -mt-6">
              <div class="text-center">
                <div class="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{{ Math.round(leadStats?.conversion_rate || 0) }}%</div>
                <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">konversiya</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== OPERATOR LEADERBOARD ===== -->
      <section class="card p-4 sm:p-6">
        <div class="flex items-start justify-between mb-4 gap-2 flex-wrap">
          <div>
            <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <Trophy class="w-4 h-4 text-amber-500" /> Eng samarali operatorlar
            </h2>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ rangeLabel }} bo'yicha qabul qilingan arizalar soni</p>
          </div>
          <RouterLink to="/director/operator-analytics"
                      class="text-xs font-semibold text-brand-700 dark:text-brand-300 hover:text-brand-800 inline-flex items-center gap-1">
            To'liq analitika <ArrowRight class="w-3 h-3" />
          </RouterLink>
        </div>

        <div v-if="!topOperators.length" class="py-12 text-center text-sm text-slate-500 dark:text-slate-400">
          Bu davrda ma'lumot yo'q
        </div>
        <ul v-else class="space-y-2.5">
          <li v-for="(op, i) in topOperators" :key="op.operator_id"
              class="flex items-center gap-3 p-3 rounded-xl ring-1 ring-slate-100 dark:ring-slate-800 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
            <!-- Rank -->
            <div class="grid place-items-center w-8 h-8 rounded-lg shrink-0 font-bold text-sm"
                 :class="i === 0 ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300'
                       : i === 1 ? 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'
                       : i === 2 ? 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300'
                                 : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'">
              <Crown v-if="i === 0" class="w-4 h-4" />
              <span v-else>{{ i + 1 }}</span>
            </div>
            <!-- Avatar -->
            <div class="grid place-items-center w-10 h-10 rounded-xl text-white font-bold text-sm shrink-0 bg-gradient-to-br shadow-sm"
                 :class="avatarColor(op.operator_id)">
              {{ initials(op.full_name) }}
            </div>
            <!-- Name + meta -->
            <div class="min-w-0 flex-1">
              <div class="font-semibold text-sm text-slate-900 dark:text-slate-100 truncate">
                {{ op.full_name || op.phone || op.operator_id.slice(0, 8) }}
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate flex flex-wrap gap-x-2 gap-y-0.5 mt-0.5">
                <span><strong class="text-slate-700 dark:text-slate-300">{{ op.applications_created || 0 }}</strong> ariza</span>
                <span><strong class="text-emerald-600 dark:text-emerald-400">{{ op.contracts_signed || 0 }}</strong> shartnoma</span>
                <span class="hidden sm:inline"><strong class="text-slate-700 dark:text-slate-300">{{ op.leads_actioned || 0 }}</strong> lead</span>
              </div>
            </div>
            <!-- Big number + conv -->
            <div class="text-right shrink-0">
              <div class="text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ op.applications_accepted || 0 }}</div>
              <div class="text-[10px] uppercase tracking-wider font-semibold"
                   :class="opConvRate(op) >= 50 ? 'text-emerald-600 dark:text-emerald-400'
                         : opConvRate(op) >= 20 ? 'text-amber-600 dark:text-amber-400'
                                                 : 'text-rose-600 dark:text-rose-400'">
                {{ opConvRate(op) }}% konversiya
              </div>
            </div>
          </li>
        </ul>
      </section>

      <!-- ===== PAYMENTS SUMMARY + TOP DEBTORS ===== -->
      <section class="grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-5">
        <!-- Payments — left, 3/5 -->
        <div class="card p-4 sm:p-6 lg:col-span-3">
          <div class="flex items-start justify-between mb-4 gap-2 flex-wrap">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <Wallet class="w-4 h-4 text-emerald-600" /> To'lovlar
            </h2>
            <RouterLink v-if="false" to="/director/payments"
                        class="text-xs font-semibold text-brand-700 dark:text-brand-300 hover:text-brand-800 inline-flex items-center gap-1">
              Batafsil <ArrowRight class="w-3 h-3" />
            </RouterLink>
          </div>

          <!-- KPI row -->
          <div class="grid grid-cols-3 gap-3 sm:gap-4 mb-4">
            <div class="rounded-xl bg-emerald-50 dark:bg-emerald-500/10 p-3 ring-1 ring-emerald-200/60 dark:ring-emerald-700/30">
              <div class="text-[10px] uppercase tracking-wider font-bold text-emerald-700 dark:text-emerald-300 mb-1">Bugun</div>
              <div class="text-lg sm:text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ fmtMoney(paymentsDash?.today_sum || 0) }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">{{ paymentsDash?.today_count || 0 }} ta</div>
            </div>
            <div class="rounded-xl bg-brand-50 dark:bg-brand-500/10 p-3 ring-1 ring-brand-200/60 dark:ring-brand-700/30">
              <div class="text-[10px] uppercase tracking-wider font-bold text-brand-700 dark:text-brand-300 mb-1">Bu oy</div>
              <div class="text-lg sm:text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ fmtMoney(paymentsDash?.month_sum || 0) }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">{{ paymentsDash?.month_count || 0 }} ta</div>
            </div>
            <div class="rounded-xl bg-amber-50 dark:bg-amber-500/10 p-3 ring-1 ring-amber-200/60 dark:ring-amber-700/30">
              <div class="text-[10px] uppercase tracking-wider font-bold text-amber-700 dark:text-amber-300 mb-1">Kutilmoqda</div>
              <div class="text-lg sm:text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ fmtMoney(paymentsDash?.pending_sum || 0) }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">{{ paymentsDash?.pending_count || 0 }} ta</div>
            </div>
          </div>

          <!-- Sparkline -->
          <div>
            <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-2">12 oylik to'lov trendi</div>
            <div class="h-40">
              <Line :data="paymentSparkData" :options="paymentSparkOpts" />
            </div>
          </div>

          <!-- Outstanding -->
          <div v-if="paymentsDash?.outstanding_total"
               class="mt-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 ring-1 ring-slate-200/60 dark:ring-slate-700/40 flex items-center gap-3">
            <CreditCard class="w-5 h-5 text-slate-400 shrink-0" />
            <div class="min-w-0 flex-1">
              <div class="text-[11px] text-slate-500 dark:text-slate-400">Umumiy qarz qoldig'i</div>
              <div class="text-base sm:text-lg font-bold tabular-nums text-rose-600 dark:text-rose-400">
                {{ fmtMoney(paymentsDash.outstanding_total) }} UZS
              </div>
            </div>
          </div>
        </div>

        <!-- Top debtors — right, 2/5 -->
        <div class="card p-4 sm:p-6 lg:col-span-2">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2 mb-4">
            <AlertTriangle class="w-4 h-4 text-rose-500" /> Eng katta qarzdorlar
          </h2>
          <ul v-if="paymentsDash?.top_debtors?.length" class="space-y-2">
            <li v-for="d in (paymentsDash.top_debtors as any[]).slice(0, 6)" :key="d.contract_id"
                class="flex items-center gap-3 p-2.5 rounded-lg ring-1 ring-slate-100 dark:ring-slate-800 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
              <div class="grid place-items-center w-9 h-9 rounded-lg bg-gradient-to-br text-white font-bold text-xs shrink-0"
                   :class="avatarColor(d.contract_id || d.applicant_full_name || '?')">
                {{ initials(d.applicant_full_name) }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{{ d.applicant_full_name || '—' }}</div>
                <div class="text-[10px] font-mono text-slate-400 dark:text-slate-500 truncate">{{ d.contract_number }}</div>
              </div>
              <div class="text-right shrink-0">
                <div class="text-sm font-bold tabular-nums text-rose-600 dark:text-rose-400">{{ fmtCompact(Number(d.balance || 0)) }}</div>
                <div class="text-[10px] text-slate-400 dark:text-slate-500">qarz</div>
              </div>
            </li>
          </ul>
          <div v-else class="py-12 text-center text-sm text-slate-500 dark:text-slate-400">
            Qarzdor topilmadi
          </div>
        </div>
      </section>

      <!-- ===== SOURCE BREAKDOWN ===== -->
      <section v-if="topSources.length" class="card p-4 sm:p-6">
        <div class="flex items-start justify-between mb-4 gap-2 flex-wrap">
          <div>
            <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <Activity class="w-4 h-4 text-amber-500" /> Lead manbalari
            </h2>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Eng samarali kanallar</p>
          </div>
        </div>
        <ul class="space-y-3">
          <li v-for="row in topSources" :key="row.name">
            <div class="flex items-baseline justify-between mb-1 gap-2">
              <span class="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{{ row.name || 'Manba ko\'rsatilmagan' }}</span>
              <span class="text-xs text-slate-500 dark:text-slate-400 tabular-nums shrink-0 ml-2">
                <strong class="text-slate-900 dark:text-slate-100">{{ row.won || 0 }}</strong> / {{ row.total || 0 }}
                <span class="ml-1.5 font-semibold"
                      :class="(row.conversion_rate || 0) >= 50 ? 'text-emerald-600 dark:text-emerald-400'
                            : (row.conversion_rate || 0) >= 20 ? 'text-amber-600 dark:text-amber-400'
                                                                  : 'text-rose-600 dark:text-rose-400'">
                  {{ Math.round(row.conversion_rate || 0) }}%
                </span>
              </span>
            </div>
            <div class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div class="h-full rounded-full transition-all"
                   :class="(row.conversion_rate || 0) >= 50 ? 'bg-emerald-500'
                         : (row.conversion_rate || 0) >= 20 ? 'bg-amber-500' : 'bg-rose-500'"
                   :style="{ width: Math.max(Number(row.conversion_rate) || 0, 2) + '%' }"></div>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
