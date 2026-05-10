<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  CreditCard, Search, Download, Filter as FilterIcon, X as XIcon,
  TrendingUp, Building2, Calendar, AlertTriangle, Wallet,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import {
  paymentsApi, type PaymentRead, type PaymentStatus, type PaymentsBreakdown,
} from '@/api/payments.api'
import { dictionariesApi, type DictionaryItem } from '@/api/dictionaries.api'
import { downloadCsv } from '@/api/http'
import { useToast } from '@/composables/useToast'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import { PAYMENT_STATUS, tr } from '@/utils/labels'

const router = useRouter()
const toast = useToast()

const items = ref<PaymentRead[]>([])
const total = ref(0)
const loading = ref(false)
const breakdown = ref<PaymentsBreakdown | null>(null)
const methods = ref<DictionaryItem[]>([])
const methodsById = computed(() => Object.fromEntries(methods.value.map(m => [m.id, m.name_uz])))

const filters = reactive({
  status: '' as PaymentStatus | '',
  payment_method_id: '' as string,
  date_from: '' as string,  // YYYY-MM-DD
  date_to: '' as string,
  page: 1,
  size: 50,
})

// Default the date range to "this month" so the page lands with useful numbers.
function thisMonthRange() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const pad = (n: number) => String(n).padStart(2, '0')
  filters.date_from = `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}`
  filters.date_to = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

const STATUS_OPTIONS = [
  { id: 'pending',   label: PAYMENT_STATUS.pending },
  { id: 'confirmed', label: PAYMENT_STATUS.confirmed },
  { id: 'failed',    label: PAYMENT_STATUS.failed },
  { id: 'refunded',  label: PAYMENT_STATUS.refunded },
]
const methodOptions = computed(() => methods.value.map(m => ({ id: m.id, label: m.name_uz })))

function isoFrom(d: string): string | undefined {
  if (!d) return undefined
  return new Date(d + 'T00:00:00').toISOString()
}
function isoTo(d: string): string | undefined {
  if (!d) return undefined
  return new Date(d + 'T23:59:59').toISOString()
}

async function loadList() {
  loading.value = true
  try {
    const res = await paymentsApi.list({
      status: filters.status || undefined,
      payment_method_id: filters.payment_method_id || undefined,
      date_from: isoFrom(filters.date_from),
      date_to: isoTo(filters.date_to),
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

async function loadBreakdown() {
  try {
    breakdown.value = await paymentsApi.breakdown({
      date_from: isoFrom(filters.date_from),
      date_to: isoTo(filters.date_to),
    })
  } catch { /* ignore */ }
}

async function loadAll() {
  await Promise.all([loadList(), loadBreakdown()])
}

watch(() => [filters.status, filters.payment_method_id, filters.date_from, filters.date_to], () => {
  filters.page = 1
  loadAll()
})
watch(() => filters.page, loadList)

onMounted(async () => {
  thisMonthRange()
  methods.value = await dictionariesApi.items('payment_methods').catch(() => [])
  await loadAll()
})

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

const activeFilterCount = computed(() => {
  let n = 0
  if (filters.status) n++
  if (filters.payment_method_id) n++
  if (filters.date_from) n++
  if (filters.date_to) n++
  return n
})
function clearFilters() {
  filters.status = ''
  filters.payment_method_id = ''
  filters.date_from = ''
  filters.date_to = ''
}
function presetThisMonth() {
  thisMonthRange()
}
function presetLast30() {
  const now = new Date()
  const past = new Date(); past.setDate(now.getDate() - 29)
  const pad = (n: number) => String(n).padStart(2, '0')
  filters.date_from = `${past.getFullYear()}-${pad(past.getMonth() + 1)}-${pad(past.getDate())}`
  filters.date_to = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
function presetToday() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
  filters.date_from = today
  filters.date_to = today
}

const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    await downloadCsv('/payments/export.csv', {
      status: filters.status || undefined,
      payment_method_id: filters.payment_method_id || undefined,
      date_from: isoFrom(filters.date_from),
      date_to: isoTo(filters.date_to),
    })
    toast.success("CSV yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}

// === Helpers ===
function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '0'
  return Math.round(n).toLocaleString('uz-UZ')
}
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}
function statusTone(s: PaymentStatus): string {
  return s === 'confirmed'
    ? 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300'
    : s === 'pending'
      ? 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300'
      : s === 'refunded'
        ? 'bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-500/10 dark:text-violet-300'
        : 'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-300'
}

const periodSubtitle = computed(() => {
  if (!breakdown.value) return ''
  return `${breakdown.value.period_count} ta tasdiqlangan to'lov · ${fmtMoney(breakdown.value.period_sum)} so'm`
})

const crumbs = [
  { label: 'Bosh sahifa', to: '/accountant' },
  { label: "To'lovlar" },
]
</script>

<template>
  <div>
    <PageHeader
      title="To'lovlar"
      :subtitle="periodSubtitle || `Jami ${total} ta yozuv`"
      :crumbs="crumbs"
    >
      <button class="btn-outline" :disabled="exporting" @click="exportCsv">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'CSV' }}
      </button>
    </PageHeader>

    <!-- Filters -->
    <div class="card p-4 mb-4 flex flex-col gap-3">
      <div class="w-full flex items-center justify-between">
        <div class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 inline-flex items-center gap-2">
          <FilterIcon class="w-3.5 h-3.5" /> Filtrlar
          <span v-if="activeFilterCount" class="px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px]">
            {{ activeFilterCount }}
          </span>
        </div>
        <div class="flex items-center gap-1.5">
          <button class="text-[11px] px-2 py-1 rounded-md text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40"
                  @click="presetToday">Bugun</button>
          <button class="text-[11px] px-2 py-1 rounded-md text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40"
                  @click="presetLast30">30 kun</button>
          <button class="text-[11px] px-2 py-1 rounded-md text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40"
                  @click="presetThisMonth">Bu oy</button>
          <button v-if="activeFilterCount"
                  class="text-[11px] px-2 py-1 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1"
                  @click="clearFilters">
            <XIcon class="w-3 h-3" /> Tozalash
          </button>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div>
          <label class="field-label">Dan</label>
          <input v-model="filters.date_from" type="date" class="input" />
        </div>
        <div>
          <label class="field-label">Gacha</label>
          <input v-model="filters.date_to" type="date" class="input" />
        </div>
        <div>
          <label class="field-label">Holati</label>
          <SearchSelect v-model="filters.status" :options="STATUS_OPTIONS" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">To'lov turi</label>
          <SearchSelect v-model="filters.payment_method_id" :options="methodOptions" placeholder="— hammasi —" allow-clear />
        </div>
      </div>
    </div>

    <!-- Period summary card -->
    <section v-if="breakdown" class="card p-5 sm:p-6 mb-4">
      <div class="flex items-center gap-2 mb-4">
        <span class="grid place-items-center w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300">
          <TrendingUp class="w-4 h-4" />
        </span>
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Davr xulosasi</h2>
        <span class="text-xs text-slate-500 dark:text-slate-400 ml-auto inline-flex items-center gap-1">
          <Calendar class="w-3 h-3" />
          {{ filters.date_from || '—' }} — {{ filters.date_to || '—' }}
        </span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
        <div class="rounded-xl p-3 ring-1 ring-emerald-200/70 dark:ring-emerald-700/40 bg-emerald-50/50 dark:bg-emerald-500/10">
          <div class="text-[10px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300 font-semibold">Jami qabul qilingan</div>
          <div class="mt-1 text-2xl font-bold tabular-nums text-emerald-700 dark:text-emerald-300">
            {{ fmtMoney(breakdown.period_sum) }} <span class="text-xs font-normal opacity-70">so'm</span>
          </div>
          <div class="mt-1 text-xs text-slate-600 dark:text-slate-400">{{ breakdown.period_count }} ta tasdiqlangan to'lov</div>
        </div>
        <div class="rounded-xl p-3 ring-1 ring-slate-200/70 dark:ring-slate-700/40 bg-slate-50/50 dark:bg-slate-800/30">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold inline-flex items-center gap-1">
            <Wallet class="w-3 h-3" /> To'lov turlari
          </div>
          <ul class="mt-1.5 space-y-1 text-xs">
            <li v-for="m in breakdown.by_method.slice(0, 3)" :key="m.method_id" class="flex items-center justify-between gap-2">
              <span class="truncate text-slate-700 dark:text-slate-300">{{ m.method_name }}</span>
              <span class="font-semibold tabular-nums text-slate-900 dark:text-slate-100">{{ fmtMoney(m.sum) }}</span>
            </li>
            <li v-if="!breakdown.by_method.length" class="text-slate-400 italic">Ma'lumot yo'q</li>
          </ul>
        </div>
        <div class="rounded-xl p-3 ring-1 ring-slate-200/70 dark:ring-slate-700/40 bg-slate-50/50 dark:bg-slate-800/30">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold inline-flex items-center gap-1">
            <Building2 class="w-3 h-3" /> Filiallar bo'yicha
          </div>
          <ul class="mt-1.5 space-y-1 text-xs">
            <li v-for="b in breakdown.by_branch.slice(0, 3)" :key="b.branch_id" class="flex items-center justify-between gap-2">
              <span class="truncate text-slate-700 dark:text-slate-300">{{ b.branch_name }}</span>
              <span class="font-semibold tabular-nums text-slate-900 dark:text-slate-100">{{ fmtMoney(b.sum) }}</span>
            </li>
            <li v-if="!breakdown.by_branch.length" class="text-slate-400 italic">Ma'lumot yo'q</li>
          </ul>
        </div>
      </div>

      <!-- Outstanding shortcut -->
      <RouterLink to="/accountant/contracts?payment_status=unpaid"
                  class="inline-flex items-center gap-2 text-sm font-medium text-rose-600 dark:text-rose-400 hover:underline">
        <AlertTriangle class="w-4 h-4" />
        Qarzdorlar ro'yxati (to'lanmagan shartnomalar) →
      </RouterLink>
    </section>

    <Skeleton v-if="loading" type="table" />
    <div v-else-if="!items.length" class="card p-6">
      <EmptyState :icon="CreditCard" title="To'lovlar topilmadi" subtitle="Filtrlarni o'zgartiring yoki sana diapazonini kengaytiring" />
    </div>

    <!-- Mobile card list (< md) -->
    <ul v-else class="md:hidden space-y-2.5">
      <li v-for="p in items" :key="p.id" class="card p-4">
        <div class="flex items-start justify-between gap-2 mb-1">
          <div class="font-semibold tabular-nums text-slate-900 dark:text-slate-100">
            {{ fmtMoney(p.amount) }} <span class="text-xs font-normal text-slate-500">{{ p.currency }}</span>
          </div>
          <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1"
                :class="statusTone(p.status)">
            {{ tr(PAYMENT_STATUS, p.status) }}
          </span>
        </div>
        <div class="font-mono text-[11px] text-slate-500 dark:text-slate-400 mb-1">{{ p.payment_number }}</div>
        <div class="text-xs text-slate-600 dark:text-slate-400 flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span>{{ methodsById[p.payment_method_id] || '—' }}</span>
          <span v-if="p.reference" class="text-slate-300 dark:text-slate-700">·</span>
          <span v-if="p.reference" class="font-mono">№{{ p.reference }}</span>
          <span class="text-slate-300 dark:text-slate-700">·</span>
          <span>{{ fmtDate(p.paid_at || p.created_at) }}</span>
        </div>
        <RouterLink :to="`/accountant/contracts/${p.contract_id}/payments`"
                    class="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-600 dark:text-brand-300 hover:underline">
          Shartnomaga o'tish →
        </RouterLink>
      </li>
    </ul>

    <!-- Mobile pagination -->
    <div v-if="!loading && items.length" class="md:hidden mt-3 flex items-center justify-between text-xs">
      <span class="text-slate-500">{{ filters.page }} / {{ lastPage() }} · jami {{ total }}</span>
      <div class="flex gap-2">
        <button class="btn-outline btn-sm" :disabled="filters.page <= 1" @click="filters.page--">‹</button>
        <button class="btn-outline btn-sm" :disabled="filters.page >= lastPage()" @click="filters.page++">›</button>
      </div>
    </div>

    <!-- Desktop table (>= md) -->
    <div v-if="!loading && items.length" class="card hidden md:block">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 dark:border-slate-800 text-[10px] uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
              <th class="text-left font-semibold px-5 py-3.5">To'lov</th>
              <th class="text-left font-semibold px-4 py-3.5">Summa</th>
              <th class="text-left font-semibold px-4 py-3.5">Turi</th>
              <th class="text-left font-semibold px-4 py-3.5">Reference</th>
              <th class="text-left font-semibold px-4 py-3.5">Vaqt</th>
              <th class="text-left font-semibold px-4 py-3.5 w-28">Holati</th>
              <th class="text-right font-semibold px-5 py-3.5 w-32">Amal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in items" :key="p.id"
                class="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors group">
              <td class="px-5 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">{{ p.payment_number }}</td>
              <td class="px-4 py-3">
                <span class="font-semibold tabular-nums text-slate-900 dark:text-slate-100">{{ fmtMoney(p.amount) }}</span>
                <span class="text-xs text-slate-500 ml-1">{{ p.currency }}</span>
              </td>
              <td class="px-4 py-3 text-xs text-slate-700 dark:text-slate-300">{{ methodsById[p.payment_method_id] || '—' }}</td>
              <td class="px-4 py-3 font-mono text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[20ch]">{{ p.reference || '—' }}</td>
              <td class="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{{ fmtDate(p.paid_at || p.created_at) }}</td>
              <td class="px-4 py-3">
                <StatusBadge :status="p.status" :label="tr(PAYMENT_STATUS, p.status)" />
              </td>
              <td class="px-5 py-3 text-right">
                <RouterLink :to="`/accountant/contracts/${p.contract_id}/payments`" class="btn-outline btn-sm">
                  Shartnoma →
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">
          Sahifa <strong class="text-slate-700 dark:text-slate-300">{{ filters.page }}</strong> / {{ lastPage() }}
          <span class="mx-1">·</span>
          Jami <strong class="text-slate-700 dark:text-slate-300">{{ total }}</strong>
        </div>
        <div class="flex gap-2">
          <button class="btn-outline btn-sm" :disabled="filters.page <= 1" @click="filters.page--">‹ Oldingi</button>
          <button class="btn-outline btn-sm" :disabled="filters.page >= lastPage()" @click="filters.page++">Keyingi ›</button>
        </div>
      </div>
    </div>
  </div>
</template>
