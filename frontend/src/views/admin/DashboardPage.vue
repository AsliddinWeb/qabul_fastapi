<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Bar, Line, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement,
  PointElement, LineElement, Filler,
} from 'chart.js'
import {
  Users as UsersIcon, ClipboardList, FilePlus2, FileEdit,
  TrendingUp, TrendingDown, Plus, ArrowRight, Activity,
  Eye, FileText, Inbox, Award, Trash2 as TrashIcon, RefreshCw,
} from 'lucide-vue-next'
import { useThemeStore } from '@/stores/theme'
import { staffApi } from '@/api/staff.api'
import { adminApi } from '@/api/admin.api'
import { http } from '@/api/http'
import { AUDIT_ACTIONS, AUDIT_ENTITY_TYPES, auditCategory } from '@/utils/labels'
import { useAuthStore } from '@/stores/auth'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Filler)

const theme = useThemeStore()
const auth = useAuthStore()

interface Counts {
  applicants: number
  applicationsByStatus: Record<string, number>
  users: number
  programs: number
  branches: number
  contracts: number
  payments: number
}

const data = ref<Counts>({
  applicants: 0,
  applicationsByStatus: { topshirildi: 0, korib_chiqilmoqda: 0, qabul_qilindi: 0, rad_etildi: 0 },
  users: 0, programs: 0, branches: 0, contracts: 0, payments: 0,
})
const trend = ref<any[]>([])
const recent = ref<any[]>([])
const bySource = ref<Array<{ source_id: string; name: string; total: number; won: number; lost: number; open: number; conversion_rate: number }>>([])
const byOperator = ref<Array<{ user_id: string; name: string; phone: string; total: number; won: number; lost: number; open: number; conversion_rate: number }>>([])
const loading = ref(true)
const range = ref<'3' | '6' | '12'>('6')

onMounted(async () => {
  try {
    const { leadsApi } = await import('@/api/leads.api')
    const [stats, applicantsTotal, users, programs, branches, audit, trendData, contracts, payments, breakdown] = await Promise.all([
      adminApi.applications.stats().catch(() => ({} as any)),
      staffApi.applicants.list({ page: 1, size: 1 }).then(r => r.total).catch(() => 0),
      adminApi.users.list({ page: 1, size: 1 }).then(r => r.total).catch(() => 0),
      adminApi.programs.list().then(r => r.length).catch(() => 0),
      adminApi.branches.list(false).then(r => r.length).catch(() => 0),
      http.get<{ items: any[] }>('/audit', { params: { page: 1, size: 6 } }).then(r => r.data.items).catch(() => []),
      adminApi.applications.trend(12).catch(() => []),
      adminApi.contracts.list({ page: 1, size: 1 }).then(r => r.total).catch(() => 0),
      adminApi.payments.list({ page: 1, size: 1 }).then(r => r.total).catch(() => 0),
      leadsApi.breakdown().catch(() => ({ by_source: [], by_operator: [] })),
    ])
    data.value = {
      applicants: applicantsTotal,
      applicationsByStatus: {
        topshirildi:        stats.topshirildi || 0,
        korib_chiqilmoqda:  stats.korib_chiqilmoqda || 0,
        qabul_qilindi:      stats.qabul_qilindi || 0,
        rad_etildi:         stats.rad_etildi || 0,
      },
      users, programs, branches, contracts, payments,
    }
    trend.value = trendData
    recent.value = audit
    bySource.value = (breakdown.by_source || []).filter((r: any) => r.total > 0).slice(0, 7)
    byOperator.value = (breakdown.by_operator || []).slice(0, 6)
  } finally {
    loading.value = false
  }
})

const totalApplications = computed(() =>
  Object.values(data.value.applicationsByStatus).reduce((a, b) => a + b, 0))

const conversionRate = computed(() => {
  const reviewed = data.value.applicationsByStatus.korib_chiqilmoqda
              + data.value.applicationsByStatus.qabul_qilindi
              + data.value.applicationsByStatus.rad_etildi
  const accepted = data.value.applicationsByStatus.qabul_qilindi
  return reviewed ? Math.round((accepted / reviewed) * 100) : 0
})

const txt = computed(() => theme.isDark ? '#cbd5e1' : '#64748b')
const grid = computed(() => theme.isDark ? 'rgba(148,163,184,0.10)' : 'rgba(100,116,139,0.10)')
const brand500 = '#3f56ef'
const brand400 = '#647ffb'
const brand200 = '#b8ccff'

const MONTH_LABELS = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']
function monthLabel(iso: string): string {
  const d = new Date(iso); return MONTH_LABELS[d.getMonth()]
}

const trendSlice = computed(() => {
  if (!trend.value.length) return []
  const n = Number(range.value)
  return trend.value.slice(-n)
})

const trendBar = computed(() => ({
  labels: trendSlice.value.map((b) => monthLabel(b.month)),
  datasets: [
    {
      label: 'Yangi',
      data: trendSlice.value.map((b) => b.topshirildi),
      backgroundColor: brand200,
      borderRadius: 6,
      stack: 'a',
    },
    {
      label: "Ko'rilmoqda",
      data: trendSlice.value.map((b) => b.korib_chiqilmoqda),
      backgroundColor: brand400,
      borderRadius: 6,
      stack: 'a',
    },
    {
      label: 'Qabul',
      data: trendSlice.value.map((b) => b.qabul_qilindi),
      backgroundColor: brand500,
      borderRadius: 6,
      stack: 'a',
    },
  ],
}))

const trendBarOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom' as const,
      align: 'start' as const,
      labels: { color: txt.value, padding: 12, usePointStyle: true, pointStyle: 'circle' as const, font: { size: 11 } },
    },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { stacked: true, ticks: { color: txt.value, font: { size: 11 } }, grid: { display: false } },
    y: { stacked: true, ticks: { color: txt.value, precision: 0 }, grid: { color: grid.value, drawBorder: false } },
  },
}))

const doughnut = computed(() => ({
  labels: ['Yangi', "Ko'rilmoqda", 'Qabul qilindi', 'Rad etildi'],
  datasets: [{
    data: [
      data.value.applicationsByStatus.topshirildi,
      data.value.applicationsByStatus.korib_chiqilmoqda,
      data.value.applicationsByStatus.qabul_qilindi,
      data.value.applicationsByStatus.rad_etildi,
    ],
    backgroundColor: [brand200, brand400, brand500, '#e2e8f0'],
    borderWidth: 0,
  }],
}))

const doughnutOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '72%',
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
}))

const pipeline = computed(() => {
  const total = totalApplications.value
  const t = data.value.applicationsByStatus.topshirildi
  const r = data.value.applicationsByStatus.korib_chiqilmoqda
  const a = data.value.applicationsByStatus.qabul_qilindi
  const c = data.value.contracts
  const p = data.value.payments
  const max = Math.max(total, 1)
  return [
    { label: 'Topshirilgan',       value: t, percent: Math.round(t * 100 / max) },
    { label: "Ko'rib chiqilmoqda", value: r, percent: Math.round(r * 100 / max) },
    { label: 'Qabul qilingan',     value: a, percent: Math.round(a * 100 / max) },
    { label: 'Shartnoma',          value: c, percent: Math.round(c * 100 / max) },
    { label: "To'lov",             value: p, percent: Math.round(p * 100 / max) },
  ]
})

function sparkline(values: number[]) {
  return {
    data: {
      labels: values.map((_, i) => i.toString()),
      datasets: [{
        data: values,
        borderColor: brand500,
        backgroundColor: brand500 + '22',
        fill: true,
        tension: 0.45,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } },
      elements: { line: { borderJoinStyle: 'round' as const } },
    },
  }
}

const sparkApplicants    = computed(() => sparkline((trend.value || []).map((b) => b.total)))
const sparkApplications  = computed(() => sparkline((trend.value || []).map((b) => b.total)))
const sparkAccepted      = computed(() => sparkline((trend.value || []).map((b) => b.qabul_qilindi)))
const sparkRejected      = computed(() => sparkline((trend.value || []).map((b) => b.rad_etildi)))

function relativeTime(iso: string): string {
  const d = new Date(iso); const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'Hozir'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} daq oldin`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat oldin`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} kun oldin`
  return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short' })
}
function userDisplay(l: any): string {
  return l.user_full_name || l.user_phone || 'Tizim'
}

const ACTIVITY_TONE: Record<string, string> = {
  create: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300',
  update: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300',
  delete: 'bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300',
  status: 'bg-amber-100 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300',
  other:  'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
}
const ACTIVITY_ICON: Record<string, any> = {
  create: FilePlus2,
  update: FileEdit,
  delete: TrashIcon,
  status: RefreshCw,
  other:  Activity,
}
const ENTITY_LABELS = AUDIT_ENTITY_TYPES

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h >= 5 && h < 12)  return 'Xayrli tong'
  if (h >= 12 && h < 17) return 'Xayrli kun'
  if (h >= 17 && h < 22) return 'Xayrli kech'
  return 'Hayrli oqshom'
})

// First word of full_name only when it looks like a real personal name —
// "Super Admin" / "Operator Test" sound robotic when truncated to "Super".
const greetName = computed(() => {
  const fn = auth.user?.full_name?.trim() || ''
  if (!fn) return ''
  const first = fn.split(/\s+/)[0]
  const generic = new Set(['admin', 'super', 'superadmin', 'operator', 'director', 'accountant', 'xiu'])
  return generic.has(first.toLowerCase()) ? '' : first
})

function trendDelta(getter: (b: any) => number): { v: number; up: boolean } {
  if (trend.value.length < 2) return { v: 0, up: true }
  const last = getter(trend.value[trend.value.length - 1])
  const prev = getter(trend.value[trend.value.length - 2])
  if (prev === 0) return { v: last > 0 ? 100 : 0, up: last >= 0 }
  const pct = Math.round(((last - prev) / prev) * 100)
  return { v: Math.abs(pct), up: pct >= 0 }
}
const dApplicants    = computed(() => trendDelta((b) => b.total))
const dApplications  = computed(() => trendDelta((b) => b.total))
const dAccepted      = computed(() => trendDelta((b) => b.qabul_qilindi))
const dRejected      = computed(() => trendDelta((b) => b.rad_etildi))

void auditCategory
</script>

<template>
  <div class="space-y-5">
    <!-- Page header with breadcrumb + action buttons -->
    <PageHeader
      :title="greetName ? `${greeting}, ${greetName}!` : `${greeting}!`"
      :subtitle="loading ? 'Yuklanmoqda...' : `Tizimda ${totalApplications} ariza · ${data.applicationsByStatus.topshirildi} ta yangi`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }]"
    >
      <RouterLink to="/admin/applications" class="btn-outline">
        <Eye class="w-4 h-4" /> Arizalar
      </RouterLink>
      <RouterLink to="/admin/applications/new" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi ariza
      </RouterLink>
    </PageHeader>

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else>
      <!-- 4 stat cards with circular icons + trend pills + sparkline -->
      <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <RouterLink to="/admin/applicants" class="block">
          <StatCard
            label="Abituriyentlar"
            :value="data.applicants"
            :icon="UsersIcon"
            tone="brand"
            :trend="dApplicants.up ? dApplicants.v : -dApplicants.v"
            trend-hint="bu oy"
          />
        </RouterLink>
        <RouterLink to="/admin/applications" class="block">
          <StatCard
            label="Arizalar"
            :value="totalApplications"
            :icon="ClipboardList"
            tone="violet"
            :trend="dApplications.up ? dApplications.v : -dApplications.v"
            trend-hint="bu oy"
          />
        </RouterLink>
        <RouterLink to="/admin/applications?status=qabul_qilindi" class="block">
          <StatCard
            label="Qabul qilindi"
            :value="data.applicationsByStatus.qabul_qilindi"
            :icon="Award"
            tone="emerald"
            :trend="dAccepted.up ? dAccepted.v : -dAccepted.v"
            trend-hint="bu oy"
          />
        </RouterLink>
        <RouterLink to="/admin/applications" class="block">
          <StatCard
            label="Konversiya"
            :value="`${conversionRate}%`"
            :icon="TrendingUp"
            tone="amber"
            hint="qabul / ko'rilgan"
          />
        </RouterLink>
      </section>

      <!-- Featured hero gradient card + secondary card with sparkline -->
      <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Hero: brand gradient with sparkline behind -->
        <div class="relative overflow-hidden rounded-2xl p-5 text-white shadow-card md:col-span-2"
             style="background: linear-gradient(135deg, #3f56ef 0%, #5b6cf5 50%, #8b5cf6 100%);">
          <div class="absolute inset-0 opacity-30" style="background-image: radial-gradient(circle at 20% 100%, rgba(255,255,255,0.2) 0%, transparent 50%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.15) 0%, transparent 60%);"></div>

          <div class="relative flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-wider opacity-80 mb-1">Jami arizalar</div>
              <div class="text-4xl font-bold tracking-tight tabular-nums">{{ totalApplications }}</div>
              <div class="mt-2 inline-flex items-center gap-2 text-sm">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-white/20 backdrop-blur">
                  <TrendingUp class="w-3 h-3" /> +{{ dApplications.v }}%
                </span>
                <span class="opacity-80 text-xs">vs o'tgan oy</span>
              </div>
            </div>
            <div class="grid place-items-center w-14 h-14 rounded-2xl bg-white/15 backdrop-blur shrink-0">
              <ClipboardList class="w-6 h-6" />
            </div>
          </div>

          <!-- Sparkline at bottom -->
          <div class="relative mt-6 h-20 -mx-1">
            <Line :data="sparkApplications.data" :options="{
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false }, tooltip: { enabled: false } },
              scales: { x: { display: false }, y: { display: false } },
              elements: {
                line: { borderColor: 'rgba(255,255,255,0.85)', borderWidth: 2.5, tension: 0.45, fill: true, backgroundColor: 'rgba(255,255,255,0.15)' },
                point: { radius: 0 },
              },
            }" />
          </div>
        </div>

        <!-- Secondary card -->
        <div class="card p-5 flex flex-col justify-between">
          <div>
            <div class="flex items-start justify-between gap-3 mb-1">
              <div class="text-sm font-medium text-slate-500 dark:text-slate-400">Bu oy qabul</div>
              <span class="grid place-items-center w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300 shrink-0">
                <Award class="w-4 h-4" />
              </span>
            </div>
            <div class="text-3xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{{ data.applicationsByStatus.qabul_qilindi }}</div>
            <div class="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold"
                 :class="dAccepted.up ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'">
              <component :is="dAccepted.up ? TrendingUp : TrendingDown" class="w-3 h-3" />
              {{ dAccepted.up ? '+' : '−' }}{{ dAccepted.v }}%
              <span class="font-normal text-slate-400 dark:text-slate-500 ml-1">vs prev</span>
            </div>
          </div>
          <div class="mt-3 h-16 -mx-1">
            <Line :data="sparkAccepted.data" :options="sparkAccepted.options" />
          </div>
        </div>
      </section>

      <!-- Trend chart + status doughnut -->
      <section class="grid lg:grid-cols-3 gap-4">
        <div class="card p-5 lg:col-span-2">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h2 class="font-semibold text-slate-900 dark:text-slate-100">Arizalar dinamikasi</h2>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Holat taqsimoti bo'yicha</p>
            </div>
            <div class="inline-flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 text-xs font-medium">
              <button class="px-2.5 py-1 rounded-md transition-colors"
                      :class="range === '3' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                      @click="range = '3'">3 oy</button>
              <button class="px-2.5 py-1 rounded-md transition-colors"
                      :class="range === '6' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                      @click="range = '6'">6 oy</button>
              <button class="px-2.5 py-1 rounded-md transition-colors"
                      :class="range === '12' ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'"
                      @click="range = '12'">12 oy</button>
            </div>
          </div>
          <div class="h-72">
            <Bar :data="trendBar" :options="trendBarOptions" />
          </div>
        </div>

        <div class="card p-5">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-4">Holat taqsimoti</h2>
          <div class="relative">
            <div class="h-48">
              <Doughnut :data="doughnut" :options="doughnutOptions" />
            </div>
            <div class="absolute inset-0 grid place-items-center pointer-events-none">
              <div class="text-center">
                <div class="text-3xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{{ totalApplications }}</div>
                <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">jami</div>
              </div>
            </div>
          </div>
          <ul class="mt-4 space-y-1.5 text-xs">
            <li class="flex items-center justify-between">
              <span class="inline-flex items-center gap-2"><span class="w-2 h-2 rounded-full" :style="{ backgroundColor: brand200 }"></span>Yangi</span>
              <strong class="text-slate-900 dark:text-slate-100 tabular-nums">{{ data.applicationsByStatus.topshirildi }}</strong>
            </li>
            <li class="flex items-center justify-between">
              <span class="inline-flex items-center gap-2"><span class="w-2 h-2 rounded-full" :style="{ backgroundColor: brand400 }"></span>Ko'rilmoqda</span>
              <strong class="text-slate-900 dark:text-slate-100 tabular-nums">{{ data.applicationsByStatus.korib_chiqilmoqda }}</strong>
            </li>
            <li class="flex items-center justify-between">
              <span class="inline-flex items-center gap-2"><span class="w-2 h-2 rounded-full" :style="{ backgroundColor: brand500 }"></span>Qabul qilindi</span>
              <strong class="text-slate-900 dark:text-slate-100 tabular-nums">{{ data.applicationsByStatus.qabul_qilindi }}</strong>
            </li>
            <li class="flex items-center justify-between">
              <span class="inline-flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600"></span>Rad etildi</span>
              <strong class="text-slate-900 dark:text-slate-100 tabular-nums">{{ data.applicationsByStatus.rad_etildi }}</strong>
            </li>
          </ul>
        </div>
      </section>

      <!-- Funnel pipeline + Recent activity -->
      <section class="grid lg:grid-cols-3 gap-4">
        <div class="card p-5 lg:col-span-2">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">Qabul jarayoni</h2>
            <RouterLink to="/admin/applications" class="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1">
              Hammasi <ArrowRight class="w-3 h-3" />
            </RouterLink>
          </div>
          <ul class="space-y-3">
            <li v-for="step in pipeline" :key="step.label">
              <div class="flex items-baseline justify-between mb-1">
                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ step.label }}</span>
                <span class="text-sm font-bold text-slate-900 dark:text-slate-100 tabular-nums">
                  {{ step.value }}
                  <span class="text-[11px] font-normal text-slate-500 dark:text-slate-400 ml-1">{{ step.percent }}%</span>
                </span>
              </div>
              <div class="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div class="h-full rounded-full bg-brand-500 transition-all"
                     :style="{ width: Math.max(step.percent, 2) + '%' }"></div>
              </div>
            </li>
          </ul>
        </div>

        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">Oxirgi faoliyat</h2>
            <RouterLink to="/admin/audit" class="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1">
              Hammasi <ArrowRight class="w-3 h-3" />
            </RouterLink>
          </div>
          <ul v-if="recent.length" class="divide-y divide-slate-100 dark:divide-slate-800/60 -my-2">
            <li v-for="log in recent" :key="log.id"
                class="py-2.5 flex items-start gap-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 -mx-2 px-2 rounded-lg transition-colors"
                @click="$router.push(`/admin/audit/${log.id}`)">
              <span class="grid place-items-center w-9 h-9 rounded-xl shrink-0" :class="ACTIVITY_TONE[auditCategory(log.action)]">
                <component :is="ACTIVITY_ICON[auditCategory(log.action)]" class="w-4 h-4" />
              </span>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-2">
                  <span class="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                    {{ AUDIT_ACTIONS[log.action] || log.action }}
                  </span>
                  <span class="text-[10px] text-slate-500 dark:text-slate-400 shrink-0">{{ relativeTime(log.created_at) }}</span>
                </div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                  <span class="text-slate-700 dark:text-slate-300 font-medium">{{ userDisplay(log) }}</span>
                  <span v-if="log.entity_type" class="text-slate-400">
                    · {{ ENTITY_LABELS[log.entity_type] || log.entity_type }}
                  </span>
                </div>
              </div>
            </li>
          </ul>
          <div v-else class="py-8 text-center text-xs text-slate-400">
            Hali faoliyat yo'q
          </div>
        </div>
      </section>

      <!-- Lead conversion stats: per source + per operator -->
      <section class="grid lg:grid-cols-2 gap-4">
        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">Lead konversiyasi (manba bo'yicha)</h2>
            <RouterLink to="/admin/leads" class="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1">
              <ArrowRight class="w-3 h-3" />
            </RouterLink>
          </div>
          <ul v-if="bySource.length" class="space-y-2.5">
            <li v-for="row in bySource" :key="row.source_id">
              <div class="flex items-baseline justify-between mb-1">
                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ row.name }}</span>
                <span class="text-xs text-slate-500 dark:text-slate-400 tabular-nums">
                  <strong class="text-slate-900 dark:text-slate-100">{{ row.won }}</strong> / {{ row.total }}
                  <span class="ml-1 font-semibold" :class="row.conversion_rate >= 50 ? 'text-emerald-600 dark:text-emerald-400' : row.conversion_rate >= 20 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-500'">
                    {{ row.conversion_rate }}%
                  </span>
                </span>
              </div>
              <div class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div class="h-full rounded-full bg-brand-500 transition-all" :style="{ width: Math.max(row.conversion_rate, 1) + '%' }"></div>
              </div>
            </li>
          </ul>
          <div v-else class="py-8 text-center text-xs text-slate-400">Lead'lar hali yo'q</div>
        </div>

        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">Operator unumdorligi</h2>
            <RouterLink to="/admin/leads" class="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1">
              <ArrowRight class="w-3 h-3" />
            </RouterLink>
          </div>
          <ul v-if="byOperator.length" class="divide-y divide-slate-100 dark:divide-slate-800/60">
            <li v-for="row in byOperator" :key="row.user_id" class="py-2 flex items-center gap-3">
              <span class="grid place-items-center w-8 h-8 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 text-[11px] font-semibold shrink-0">
                {{ (row.name || '').split(/\s+/).map(w => w[0]).slice(0,2).join('').toUpperCase() || '—' }}
              </span>
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{{ row.name }}</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 tabular-nums">
                  Jami: {{ row.total }} · Konversiya: {{ row.won }} · Faol: {{ row.open }}
                </div>
              </div>
              <span class="text-sm font-bold tabular-nums shrink-0"
                    :class="row.conversion_rate >= 50 ? 'text-emerald-600 dark:text-emerald-400' : row.conversion_rate >= 20 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-500'">
                {{ row.conversion_rate }}%
              </span>
            </li>
          </ul>
          <div v-else class="py-8 text-center text-xs text-slate-400">Operator biriktirilgan lead'lar yo'q</div>
        </div>
      </section>

      <!-- Quick links -->
      <section class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <RouterLink to="/admin/applications/new"
                    class="card p-4 hover:shadow-md transition-all flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <ClipboardList class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Yangi ariza</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">topshirish</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>

        <RouterLink to="/admin/applicants"
                    class="card p-4 hover:shadow-md transition-all flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <UsersIcon class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Abituriyentlar</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">ro'yxat</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>

        <RouterLink to="/admin/contract-templates"
                    class="card p-4 hover:shadow-md transition-all flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <FileText class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Shartnoma shabloni</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">tahrirlash</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>

        <RouterLink to="/admin/users"
                    class="card p-4 hover:shadow-md transition-all flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <UsersIcon class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Foydalanuvchilar</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">boshqaruv</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>
      </section>
    </template>
  </div>
</template>
