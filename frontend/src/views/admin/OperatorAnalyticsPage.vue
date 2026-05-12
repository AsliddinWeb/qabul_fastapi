<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ClipboardList, FileText, CreditCard, TrendingUp,
  RefreshCcw, Download, ChevronRight,
} from 'lucide-vue-next'
import { adminApi, type OperatorStatsRead } from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const route = useRoute()
const toast = useToast()

// Which panel-prefix to point detail links at — derived from the current
// path so the same component serves /admin and /director.
const panelPrefix = computed(() => route.path.startsWith('/director/') ? '/director' : '/admin')

// ---------- Date range ----------
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

function isoDay(d: Date): string {
  return d.toISOString().slice(0, 10)
}

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
const items = ref<OperatorStatsRead[]>([])
// Previous-equivalent-period totals power the "+X% vs ..." pill on each
// summary StatCard.
const prevItems = ref<OperatorStatsRead[]>([])
const downloading = ref(false)

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
    if (typeof av === 'string' && typeof bv === 'string') return av.localeCompare(bv) * dir
    return ((Number(av) || 0) - (Number(bv) || 0)) * dir
  })
})

// ---------- Totals + trend ----------
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

function trendPct(key: string): number | null {
  const cur = totals.value[key] || 0
  const prev = prevTotals.value[key] || 0
  if (cur === 0 && prev === 0) return null
  if (prev === 0) return 100
  return Math.round(((cur - prev) / prev) * 100)
}

// ---------- Formatting ----------
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

onMounted(() => {
  applyPreset('30d')
  loadLeaderboard()
})

watch([fromDate, toDate], loadLeaderboard)
</script>

<template>
  <div>
    <PageHeader title="Operatorlar analitikasi"
                subtitle="Har bir operator bo'yicha leadlar, arizalar, shartnomalar va to'lovlar bo'yicha jami ko'rsatkichlar. Tafsilot uchun jadvaldan operatorni tanlang." />

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
              <th class="px-3 py-3"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
            <tr v-for="row in sortedItems" :key="row.operator_id"
                class="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition"
                @click="$router.push(`${panelPrefix}/operator-analytics/${row.operator_id}`)">
              <td class="px-4 py-3 sticky left-0 bg-white dark:bg-slate-900 z-10">
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
              <td class="px-3 py-3 text-right">
                <ChevronRight class="w-4 h-4 text-slate-400 inline-block" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
