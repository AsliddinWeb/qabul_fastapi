<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  CreditCard, AlertTriangle, Wallet, ArrowRight, FileText, Clock, TrendingUp, TrendingDown,
} from 'lucide-vue-next'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js'
import { paymentsApi, type AccountantDashboardResponse } from '@/api/payments.api'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const auth = useAuthStore()
const theme = useThemeStore()

const data = ref<AccountantDashboardResponse | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    data.value = await paymentsApi.dashboard()
  } finally {
    loading.value = false
  }
})

function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '0'
  return Math.round(n).toLocaleString('uz-UZ')
}

const MONTHS = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']
function fmtMonth(ym: string): string {
  const m = parseInt(ym.split('-')[1] || '0', 10)
  return MONTHS[m - 1] || ym
}

// === Trend deltas ===
const monthDelta = computed(() => {
  const t = data.value?.monthly_trend
  if (!t || t.length < 2) return 0
  const last = Number(t[t.length - 1].sum) || 0
  const prev = Number(t[t.length - 2].sum) || 0
  if (prev === 0) return last > 0 ? 100 : 0
  return Math.round(((last - prev) / prev) * 100)
})

// === Sparkline ===
const txt = computed(() => theme.isDark ? '#cbd5e1' : '#64748b')
const monthlyChart = computed(() => {
  const t = data.value?.monthly_trend || []
  return {
    data: {
      labels: t.map(b => fmtMonth(b.month)),
      datasets: [{
        label: "Aylanma (so'm)",
        data: t.map(b => Number(b.sum) || 0),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.15)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: '#10b981',
        borderWidth: 2.5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx: any) => fmtMoney(ctx.parsed.y) + " so'm",
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: txt.value } },
        y: {
          grid: { color: theme.isDark ? 'rgba(148,163,184,0.1)' : 'rgba(148,163,184,0.2)' },
          ticks: {
            color: txt.value,
            callback: (v: number) => v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : fmtMoney(v),
          },
        },
      },
    },
  }
})

// === Greeting ===
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
  const generic = new Set(['admin', 'super', 'superadmin', 'operator', 'director', 'accountant', 'buxgalter', 'xiu'])
  return generic.has(first.toLowerCase()) ? '' : first
})
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      :title="greetName ? `${greeting}, ${greetName}!` : `${greeting}!`"
      :subtitle="loading
        ? 'Yuklanmoqda...'
        : `Bugun ${data?.today_count ?? 0} ta to'lov · Kutilayotgan: ${data?.pending_count ?? 0} · Umumiy qarz: ${fmtMoney(data?.outstanding_total ?? 0)} so'm`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/accountant' }]"
    >
      <RouterLink to="/accountant/contracts" class="btn-primary">
        <FileText class="w-4 h-4" /> Shartnomalar
      </RouterLink>
    </PageHeader>

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else-if="data">
      <!-- KPI tiles -->
      <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Bugun qabul qilingan"
          :value="`${fmtMoney(data.today_sum)} so'm`"
          :icon="CreditCard"
          tone="emerald"
          :hint="`${data.today_count} ta tasdiqlangan to'lov`"
        />
        <StatCard
          label="Bu oy aylanma"
          :value="`${fmtMoney(data.month_sum)} so'm`"
          :icon="Wallet"
          tone="brand"
          :trend="monthDelta"
          trend-hint="vs o'tgan oy"
          :hint="`${data.month_count} ta to'lov`"
        />
        <RouterLink to="/accountant/contracts" class="block">
          <StatCard
            label="Kutilayotgan to'lovlar"
            :value="data.pending_count"
            :icon="Clock"
            :tone="data.pending_count > 0 ? 'amber' : 'slate'"
            :hint="`${fmtMoney(data.pending_sum)} so'm tasdiqlash kutmoqda`"
          />
        </RouterLink>
        <StatCard
          label="Umumiy qarz"
          :value="`${fmtMoney(data.outstanding_total)} so'm`"
          :icon="AlertTriangle"
          :tone="Number(data.outstanding_total) > 0 ? 'rose' : 'slate'"
          hint="Barcha shartnomalar bo'yicha qoldiq"
        />
      </section>

      <!-- Monthly trend chart -->
      <section class="card p-5 sm:p-6">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">6 oylik aylanma trendi</h2>
            <p class="text-xs text-slate-500 dark:text-slate-400">Tasdiqlangan to'lovlar oylik summasi</p>
          </div>
          <span class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-md"
                :class="monthDelta >= 0
                  ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300'
                  : 'bg-rose-50 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300'">
            <component :is="monthDelta >= 0 ? TrendingUp : TrendingDown" class="w-3 h-3" />
            {{ monthDelta >= 0 ? '+' : '' }}{{ monthDelta }}%
          </span>
        </div>
        <div class="h-64 sm:h-72">
          <Line :data="monthlyChart.data" :options="monthlyChart.options" />
        </div>
      </section>

      <!-- Top debtors -->
      <section class="card overflow-hidden">
        <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
          <div class="flex items-center gap-3 min-w-0">
            <span class="grid place-items-center w-9 h-9 rounded-xl bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-300 shrink-0">
              <AlertTriangle class="w-4 h-4" />
            </span>
            <div class="min-w-0">
              <h2 class="font-semibold text-slate-900 dark:text-slate-100">Eng katta qarzdorlar</h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">Top 5 — to'liq to'lanmagan shartnomalar</p>
            </div>
          </div>
          <RouterLink to="/accountant/contracts"
                      class="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1">
            Hammasi <ArrowRight class="w-3 h-3" />
          </RouterLink>
        </div>
        <ul v-if="data.top_debtors.length" class="divide-y divide-slate-100 dark:divide-slate-800/60">
          <li v-for="(d, i) in data.top_debtors" :key="d.contract_id"
              class="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors flex items-center gap-3">
            <span class="grid place-items-center w-9 h-9 rounded-xl bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300 text-sm font-bold shrink-0">
              {{ i + 1 }}
            </span>
            <RouterLink :to="`/accountant/contracts/${d.contract_id}/payments`" class="flex-1 min-w-0">
              <div class="font-semibold text-slate-900 dark:text-slate-100 truncate">{{ d.applicant_full_name || '—' }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 inline-flex items-center gap-1.5">
                <FileText class="w-3 h-3" />
                <span class="font-mono">{{ d.contract_number }}</span>
                <span class="text-slate-300 dark:text-slate-700">·</span>
                <span>{{ fmtMoney(d.paid_amount) }} / {{ fmtMoney(d.total_amount) }} so'm</span>
              </div>
            </RouterLink>
            <div class="text-right shrink-0">
              <div class="font-bold text-rose-600 dark:text-rose-400 tabular-nums">
                {{ fmtMoney(d.balance) }}
              </div>
              <div class="text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wider">qoldiq</div>
            </div>
          </li>
        </ul>
        <div v-else class="p-12 text-center">
          <div class="inline-grid place-items-center w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300 mb-3">
            <CreditCard class="w-5 h-5" />
          </div>
          <div class="text-sm font-medium text-slate-700 dark:text-slate-300">Qarzdor yo'q!</div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Barcha shartnomalar to'liq to'langan</p>
        </div>
      </section>
    </template>
  </div>
</template>
