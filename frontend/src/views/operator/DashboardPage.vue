<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  UserPlus, Users, ClipboardList, LayoutDashboard, Phone, Send,
  TrendingUp, TrendingDown, AlertTriangle, Award, Target, Clock,
  ArrowRight, Activity, Plus,
} from 'lucide-vue-next'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js'
import { staffApi } from '@/api/staff.api'
import { leadsApi, type Lead, type LeadActivity, type LeadStats } from '@/api/leads.api'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { formatPhone } from '@/utils/validators'
import { AUDIT_ACTIONS } from '@/utils/labels'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const auth = useAuthStore()
const theme = useThemeStore()
const meId = computed(() => auth.user?.id || '')

// ---- State ----
const loading = ref(true)
const stats = ref<LeadStats | null>(null)
const myLeads = ref<Lead[]>([])
const slaAlerts = ref<Array<Lead & { last_alert_at: string | null }>>([])
const myActivities = ref<LeadActivity[]>([])
const monthlyTrend = ref<Array<{ month: string; total: number; won: number; lost: number; conv: number }>>([])
const operatorRow = ref<{ user_id: string; name: string; total: number; won: number; lost: number; open: number; conversion_rate: number } | null>(null)
const applicantsCount = ref(0)

// ---- Computed: scheduled tasks (today + overdue) based on next_contact_at ----
const scheduledTasks = computed(() => {
  const endOfToday = new Date(); endOfToday.setHours(23, 59, 59, 999)
  return myLeads.value
    .filter(l => l.status === 'open' && l.next_contact_at)
    .filter(l => new Date(l.next_contact_at!).getTime() <= endOfToday.getTime())
    .sort((a, b) => new Date(a.next_contact_at!).getTime() - new Date(b.next_contact_at!).getTime())
    .slice(0, 8)
})
const overdueTasksCount = computed(() => {
  const now = Date.now()
  return myLeads.value
    .filter(l => l.status === 'open' && l.next_contact_at)
    .filter(l => new Date(l.next_contact_at!).getTime() < now)
    .length
})

// ---- Computed: needs-contact list (no last_contact in 24h, no scheduled task) ----
const needsContactToday = computed(() => {
  const cutoff = Date.now() - 24 * 60 * 60 * 1000
  const scheduledIds = new Set(scheduledTasks.value.map(l => l.id))
  return myLeads.value
    .filter(l => l.status === 'open')
    .filter(l => !scheduledIds.has(l.id))
    .filter(l => !l.last_contact_at || new Date(l.last_contact_at).getTime() < cutoff)
    .sort((a, b) => {
      const ta = a.last_contact_at ? new Date(a.last_contact_at).getTime() : 0
      const tb = b.last_contact_at ? new Date(b.last_contact_at).getTime() : 0
      return ta - tb
    })
    .slice(0, 8)
})

function taskStatus(iso: string): 'overdue' | 'today' {
  return new Date(iso).getTime() < Date.now() ? 'overdue' : 'today'
}
function fmtTaskTime(iso: string): string {
  const d = new Date(iso)
  const isToday = d.toDateString() === new Date().toDateString()
  if (isToday) {
    return d.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleString('uz-UZ', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

const openCount     = computed(() => myLeads.value.filter(l => l.status === 'open').length)
const wonThisMonth  = computed(() => {
  const start = new Date(); start.setDate(1); start.setHours(0,0,0,0)
  return myLeads.value.filter(l => l.status === 'won' && l.converted_at && new Date(l.converted_at) >= start).length
})
const lostThisMonth = computed(() => {
  const start = new Date(); start.setDate(1); start.setHours(0,0,0,0)
  return myLeads.value.filter(l => l.status === 'lost' && l.lost_at && new Date(l.lost_at) >= start).length
})
const conversion    = computed(() => {
  const totalClosed = wonThisMonth.value + lostThisMonth.value
  return totalClosed ? Math.round((wonThisMonth.value / totalClosed) * 100) : 0
})

// Monthly trend deltas
const wonDelta = computed(() => {
  if (monthlyTrend.value.length < 2) return 0
  const last = monthlyTrend.value[monthlyTrend.value.length - 1].won
  const prev = monthlyTrend.value[monthlyTrend.value.length - 2].won
  if (prev === 0) return last > 0 ? 100 : 0
  return Math.round(((last - prev) / prev) * 100)
})
const convDelta = computed(() => {
  if (monthlyTrend.value.length < 2) return 0
  const last = monthlyTrend.value[monthlyTrend.value.length - 1].conv
  const prev = monthlyTrend.value[monthlyTrend.value.length - 2].conv
  return last - prev
})

// ---- Sparkline data ----
const txt = computed(() => theme.isDark ? '#cbd5e1' : '#64748b')
const brand500 = '#3f56ef'
function spark(values: number[]) {
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
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } },
    },
  }
}
const sparkConv = computed(() => spark(monthlyTrend.value.map(b => b.conv)))
const sparkWon  = computed(() => spark(monthlyTrend.value.map(b => b.won)))

// ---- Greeting ----
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h >= 5 && h < 12)  return 'Xayrli tong'
  if (h >= 12 && h < 17) return 'Xayrli kun'
  if (h >= 17 && h < 22) return 'Xayrli kech'
  return 'Hayrli oqshom'
})

const greetName = computed(() => {
  const fn = auth.user?.full_name?.trim() || ''
  if (!fn) return ''
  const first = fn.split(/\s+/)[0]
  const generic = new Set(['admin', 'super', 'superadmin', 'operator', 'director', 'accountant', 'xiu'])
  return generic.has(first.toLowerCase()) ? '' : first
})

// ---- Time format ----
function relativeTime(iso: string | null): string {
  if (!iso) return 'hech qachon'
  const d = new Date(iso); const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'hozirgina'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} daq oldin`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat oldin`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} kun oldin`
  return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short' })
}

function staleHours(iso: string | null): number {
  if (!iso) return 999
  return Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
}

const MONTHS = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']

// ---- Build per-month trend from my leads ----
function buildTrend() {
  const buckets: Record<string, { total: number; won: number; lost: number }> = {}
  const now = new Date()
  // Last 6 months
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    buckets[key] = { total: 0, won: 0, lost: 0 }
  }
  for (const l of myLeads.value) {
    const d = new Date(l.created_at)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    if (key in buckets) {
      buckets[key].total += 1
      if (l.status === 'won')  buckets[key].won  += 1
      if (l.status === 'lost') buckets[key].lost += 1
    }
  }
  monthlyTrend.value = Object.entries(buckets).map(([month, b]) => ({
    month,
    total: b.total,
    won: b.won,
    lost: b.lost,
    conv: (b.won + b.lost) > 0 ? Math.round((b.won / (b.won + b.lost)) * 100) : 0,
  }))
}

onMounted(async () => {
  try {
    const [leadsResp, breakdown, slaList, allActivities, applicantsResp] = await Promise.all([
      leadsApi.list({ assigned_to_id: meId.value, page: 1, size: 200 }).catch(() => ({ items: [], total: 0 } as any)),
      leadsApi.breakdown().catch(() => ({ by_source: [], by_operator: [] })),
      leadsApi.slaAlerts(72).catch(() => []),
      // Pull recent lead activities and filter by me
      Promise.resolve([]),
      staffApi.applicants.list({ page: 1, size: 1 }).catch(() => ({ total: 0 } as any)),
    ])
    myLeads.value = leadsResp.items || []
    operatorRow.value = (breakdown.by_operator || []).find(r => r.user_id === meId.value) || null
    slaAlerts.value = (slaList || []).filter(l => l.assigned_to_id === meId.value)
    myActivities.value = allActivities
    applicantsCount.value = applicantsResp.total || 0
    buildTrend()
  } finally {
    loading.value = false
  }
})

const _unused = AUDIT_ACTIONS
void _unused
</script>

<template>
  <div class="space-y-6">
    <!-- Page header with breadcrumb + quick actions -->
    <PageHeader
      :title="greetName ? `${greeting}, ${greetName}!` : `${greeting}!`"
      :subtitle="loading
        ? 'Yuklanmoqda...'
        : scheduledTasks.length > 0
          ? `Bugun ${scheduledTasks.length} ta vazifa rejada. Ochiq lead'lar: ${openCount}.`
          : `Bugun ${needsContactToday.length} ta lead bilan aloqa qilish kerak. Ochiq lead'lar: ${openCount}.`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/operator' }]"
    >
      <RouterLink to="/operator/leads/new" class="btn-outline">
        <Plus class="w-4 h-4" /> Yangi lead
      </RouterLink>
      <RouterLink to="/operator/leads/board" class="btn-primary">
        <LayoutDashboard class="w-4 h-4" /> Varonka
      </RouterLink>
    </PageHeader>

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else>
      <!-- KPI cards -->
      <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <RouterLink to="/operator/leads" class="block">
          <StatCard
            label="Mening ochiq lead'larim"
            :value="openCount"
            :icon="Users"
            tone="brand"
            :hint="`${myLeads.length} jami biriktirilgan`"
          />
        </RouterLink>
        <RouterLink to="/operator/leads?status=won" class="block">
          <StatCard
            label="Bu oy yutilgan"
            :value="wonThisMonth"
            :icon="Award"
            tone="emerald"
            :trend="wonDelta"
            trend-hint="vs o'tgan oy"
          />
        </RouterLink>
        <StatCard
          label="Konversiya (oy)"
          :value="`${conversion}%`"
          :icon="Target"
          tone="violet"
          :trend="convDelta"
          trend-hint="vs o'tgan oy"
        />
        <RouterLink to="/operator/leads" class="block">
          <StatCard
            label="SLA buzilishi"
            :value="slaAlerts.length"
            :icon="AlertTriangle"
            :tone="slaAlerts.length > 0 ? 'rose' : 'slate'"
            hint="72 soat ichida aloqasiz"
          />
        </RouterLink>
      </section>

      <!-- Featured hero gradient + sparkline -->
      <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="relative overflow-hidden rounded-2xl p-4 sm:p-5 text-white shadow-card md:col-span-2"
             style="background: linear-gradient(135deg, #3f56ef 0%, #5b6cf5 50%, #8b5cf6 100%);">
          <div class="absolute inset-0 opacity-30"
               style="background-image: radial-gradient(circle at 20% 100%, rgba(255,255,255,0.2) 0%, transparent 50%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.15) 0%, transparent 60%);"></div>
          <div class="relative flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-wider opacity-80 mb-1">Mening konversiya darajam</div>
              <div class="text-4xl font-bold tracking-tight tabular-nums">{{ operatorRow?.conversion_rate ?? conversion }}%</div>
              <div class="mt-2 inline-flex items-center gap-2 text-sm">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-white/20 backdrop-blur">
                  <component :is="convDelta >= 0 ? TrendingUp : TrendingDown" class="w-3 h-3" />
                  {{ convDelta >= 0 ? '+' : '' }}{{ convDelta }} pp
                </span>
                <span class="opacity-80 text-xs">vs o'tgan oy</span>
              </div>
              <div class="mt-3 grid grid-cols-3 gap-3 text-xs opacity-90">
                <div>
                  <div class="text-[10px] uppercase tracking-wider opacity-70">Yutilgan</div>
                  <div class="text-base font-semibold tabular-nums">{{ operatorRow?.won ?? wonThisMonth }}</div>
                </div>
                <div>
                  <div class="text-[10px] uppercase tracking-wider opacity-70">Yo'qotilgan</div>
                  <div class="text-base font-semibold tabular-nums">{{ operatorRow?.lost ?? lostThisMonth }}</div>
                </div>
                <div>
                  <div class="text-[10px] uppercase tracking-wider opacity-70">Faol</div>
                  <div class="text-base font-semibold tabular-nums">{{ operatorRow?.open ?? openCount }}</div>
                </div>
              </div>
            </div>
            <div class="grid place-items-center w-14 h-14 rounded-2xl bg-white/15 backdrop-blur shrink-0">
              <Target class="w-6 h-6" />
            </div>
          </div>
          <div class="relative mt-6 h-20 -mx-1">
            <Line :data="sparkConv.data" :options="{
              responsive: true, maintainAspectRatio: false,
              plugins: { legend: { display: false }, tooltip: { enabled: false } },
              scales: { x: { display: false }, y: { display: false } },
              elements: {
                line: { borderColor: 'rgba(255,255,255,0.85)', borderWidth: 2.5, tension: 0.45, fill: true, backgroundColor: 'rgba(255,255,255,0.15)' },
                point: { radius: 0 },
              },
            }" />
          </div>
        </div>

        <!-- Won this month with sparkline -->
        <div class="card p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div class="flex items-start justify-between gap-3 mb-1">
              <div class="text-sm font-medium text-slate-500 dark:text-slate-400">Bu oy yutilgan</div>
              <span class="grid place-items-center w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300 shrink-0">
                <Award class="w-4 h-4" />
              </span>
            </div>
            <div class="text-3xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{{ wonThisMonth }}</div>
            <div class="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold"
                 :class="wonDelta >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'">
              <component :is="wonDelta >= 0 ? TrendingUp : TrendingDown" class="w-3 h-3" />
              {{ wonDelta >= 0 ? '+' : '' }}{{ wonDelta }}%
              <span class="font-normal text-slate-400 dark:text-slate-500 ml-1">vs prev</span>
            </div>
          </div>
          <div class="mt-3 h-16 -mx-1">
            <Line :data="sparkWon.data" :options="sparkWon.options" />
          </div>
        </div>
      </section>

      <!-- Bugungi vazifalarim (next_contact_at scheduled) -->
      <section class="card overflow-hidden">
        <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
          <div class="flex items-center gap-3 min-w-0">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-300 shrink-0">
              <Target class="w-5 h-5" />
            </span>
            <div class="min-w-0">
              <h2 class="font-semibold text-slate-900 dark:text-slate-100">Bugungi vazifalarim</h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">
                Rejalashtirilgan qo'ng'iroqlar va aloqalar
                <span v-if="overdueTasksCount > 0" class="ml-1 text-rose-600 dark:text-rose-400 font-semibold">· {{ overdueTasksCount }} ta muddati o'tgan</span>
              </p>
            </div>
          </div>
          <span v-if="scheduledTasks.length" class="text-xs font-bold tabular-nums px-2 py-0.5 rounded-md bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300">
            {{ scheduledTasks.length }}
          </span>
        </div>
        <ul v-if="scheduledTasks.length" class="divide-y divide-slate-100 dark:divide-slate-800/60">
          <li v-for="l in scheduledTasks" :key="l.id"
              class="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors flex items-center gap-3">
            <span class="grid place-items-center w-12 h-12 rounded-xl shrink-0 text-xs font-bold tabular-nums"
                  :class="taskStatus(l.next_contact_at!) === 'overdue'
                    ? 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300'
                    : 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300'">
              {{ fmtTaskTime(l.next_contact_at!) }}
            </span>
            <RouterLink :to="`/operator/leads/${l.id}`" class="flex-1 min-w-0">
              <div class="font-semibold text-slate-900 dark:text-slate-100 truncate text-sm">{{ l.full_name }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-1.5">
                <span class="font-mono">{{ formatPhone(l.phone) }}</span>
                <span v-if="l.next_contact_note" class="text-slate-300 dark:text-slate-700">·</span>
                <span v-if="l.next_contact_note" class="truncate italic">{{ l.next_contact_note }}</span>
              </div>
            </RouterLink>
            <a :href="`tel:${l.phone}`"
               class="grid place-items-center w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-300 dark:hover:bg-emerald-500/25 transition-colors shrink-0"
               title="Qo'ng'iroq qilish">
              <Phone class="w-4 h-4" />
            </a>
            <a v-if="l.telegram_username"
               :href="`https://t.me/${l.telegram_username}`" target="_blank" rel="noopener"
               class="grid place-items-center w-9 h-9 rounded-lg bg-sky-50 text-sky-600 hover:bg-sky-100 dark:bg-sky-500/15 dark:text-sky-300 dark:hover:bg-sky-500/25 transition-colors shrink-0"
               title="Telegram">
              <Send class="w-4 h-4" />
            </a>
          </li>
        </ul>
        <div v-else class="p-12 text-center">
          <div class="inline-grid place-items-center w-12 h-12 rounded-2xl bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-300 mb-3">
            <Target class="w-5 h-5" />
          </div>
          <div class="text-sm font-medium text-slate-700 dark:text-slate-300">Bugun rejalashtirilgan vazifa yo'q</div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Lead detail sahifasida "Keyingi aloqa" o'rnating</p>
        </div>
      </section>

      <!-- Two columns: Today's contact list + SLA breach list -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Bugun aloqa qilish kerak -->
        <div class="card overflow-hidden">
          <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
            <div class="flex items-center gap-3 min-w-0">
              <span class="grid place-items-center w-9 h-9 rounded-xl bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300 shrink-0">
                <Clock class="w-4 h-4" />
              </span>
              <div class="min-w-0">
                <h2 class="font-semibold text-slate-900 dark:text-slate-100">Aloqa qilish kerak</h2>
                <p class="text-xs text-slate-500 dark:text-slate-400">24 soatdan beri aloqasiz lead'lar</p>
              </div>
            </div>
            <RouterLink to="/operator/leads" class="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1">
              Hammasi <ArrowRight class="w-3 h-3" />
            </RouterLink>
          </div>
          <ul v-if="needsContactToday.length" class="divide-y divide-slate-100 dark:divide-slate-800/60">
            <li v-for="l in needsContactToday" :key="l.id"
                class="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors flex items-center gap-3">
              <RouterLink :to="`/operator/leads/${l.id}`" class="flex-1 min-w-0">
                <div class="font-semibold text-slate-900 dark:text-slate-100 truncate text-sm">{{ l.full_name }}</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-1.5">
                  <span class="font-mono">{{ formatPhone(l.phone) }}</span>
                  <span class="text-slate-300 dark:text-slate-700">·</span>
                  <span class="inline-flex items-center gap-1">
                    <Clock class="w-3 h-3" />
                    {{ relativeTime(l.last_contact_at) }}
                  </span>
                  <span v-if="l.stage_name" class="text-slate-300 dark:text-slate-700">·</span>
                  <span v-if="l.stage_name" class="truncate">{{ l.stage_name }}</span>
                </div>
              </RouterLink>
              <a :href="`tel:${l.phone}`"
                 class="grid place-items-center w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-300 dark:hover:bg-emerald-500/25 transition-colors shrink-0"
                 title="Qo'ng'iroq qilish">
                <Phone class="w-4 h-4" />
              </a>
              <a v-if="l.telegram_username"
                 :href="`https://t.me/${l.telegram_username}`" target="_blank" rel="noopener"
                 class="grid place-items-center w-9 h-9 rounded-lg bg-sky-50 text-sky-600 hover:bg-sky-100 dark:bg-sky-500/15 dark:text-sky-300 dark:hover:bg-sky-500/25 transition-colors shrink-0"
                 title="Telegram">
                <Send class="w-4 h-4" />
              </a>
            </li>
          </ul>
          <div v-else class="p-12 text-center">
            <div class="inline-grid place-items-center w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300 mb-3">
              <Award class="w-5 h-5" />
            </div>
            <div class="text-sm font-medium text-slate-700 dark:text-slate-300">Hammasi joyida!</div>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Bugun aloqa kutayotgan lead yo'q</p>
          </div>
        </div>

        <!-- SLA buzilishi -->
        <div class="card overflow-hidden">
          <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
            <div class="flex items-center gap-3 min-w-0">
              <span class="grid place-items-center w-9 h-9 rounded-xl bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-300 shrink-0">
                <AlertTriangle class="w-4 h-4" />
              </span>
              <div class="min-w-0">
                <h2 class="font-semibold text-slate-900 dark:text-slate-100">SLA buzilishi</h2>
                <p class="text-xs text-slate-500 dark:text-slate-400">72 soatdan ortiq aloqasiz</p>
              </div>
            </div>
            <span v-if="slaAlerts.length" class="text-xs font-bold tabular-nums px-2 py-0.5 rounded-md bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300">
              {{ slaAlerts.length }}
            </span>
          </div>
          <ul v-if="slaAlerts.length" class="divide-y divide-slate-100 dark:divide-slate-800/60">
            <li v-for="l in slaAlerts.slice(0, 8)" :key="l.id"
                class="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors flex items-center gap-3">
              <RouterLink :to="`/operator/leads/${l.id}`" class="flex-1 min-w-0">
                <div class="font-semibold text-slate-900 dark:text-slate-100 truncate text-sm">{{ l.full_name }}</div>
                <div class="text-[11px] mt-0.5 flex items-center gap-1.5">
                  <span class="font-mono text-slate-500 dark:text-slate-400">{{ formatPhone(l.phone) }}</span>
                  <span class="text-slate-300 dark:text-slate-700">·</span>
                  <span class="inline-flex items-center gap-1 text-rose-600 dark:text-rose-400 font-semibold">
                    <Clock class="w-3 h-3" />
                    {{ staleHours(l.last_contact_at || l.stage_entered_at) }}h
                  </span>
                </div>
              </RouterLink>
              <a :href="`tel:${l.phone}`"
                 class="grid place-items-center w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-300 dark:hover:bg-emerald-500/25 transition-colors shrink-0"
                 title="Qo'ng'iroq qilish">
                <Phone class="w-4 h-4" />
              </a>
            </li>
          </ul>
          <div v-else class="p-12 text-center">
            <div class="inline-grid place-items-center w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300 mb-3">
              <Award class="w-5 h-5" />
            </div>
            <div class="text-sm font-medium text-slate-700 dark:text-slate-300">SLA toza!</div>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Hozircha buzilish yo'q</p>
          </div>
        </div>
      </section>

      <!-- Quick actions -->
      <section class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <RouterLink to="/operator/leads/new" class="card-hover p-4 flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-300">
              <Users class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Yangi lead</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">qabul qilish</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>

        <RouterLink to="/operator/applicants/new" class="card-hover p-4 flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-brand-100 text-brand-600 dark:bg-brand-500/20 dark:text-brand-200">
              <UserPlus class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Yangi abituriyent</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">qo'lda kiritish</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>

        <RouterLink to="/operator/applications" class="card-hover p-4 flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
              <ClipboardList class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Arizalar</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">{{ applicantsCount }} jami</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>

        <RouterLink to="/operator/contracts" class="card-hover p-4 flex items-center justify-between gap-3 group">
          <div class="inline-flex items-center gap-3">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-teal-100 text-teal-600 dark:bg-teal-500/20 dark:text-teal-300">
              <Activity class="w-4 h-4" />
            </span>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Shartnomalar</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400">tasdiqlash</div>
            </div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition" />
        </RouterLink>
      </section>
    </template>
  </div>
</template>
