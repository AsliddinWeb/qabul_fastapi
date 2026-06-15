<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  FileText, Search, Download, Filter as FilterIcon, X as XIcon,
  CheckCircle2, Clock, AlertTriangle, ArrowRight, Eye, CreditCard,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import {
  contractsApi,
  type ContractListItem,
  type ContractStatus,
  type PaymentStatusFilter,
} from '@/api/contracts.api'
import { downloadCsv } from '@/api/http'
import { adminApi } from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import { CONTRACT_STATUS, tr } from '@/utils/labels'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const items = ref<ContractListItem[]>([])
const total = ref(0)
const loading = ref(false)

const filters = reactive({
  status: '' as ContractStatus | '',
  payment_status: '' as PaymentStatusFilter | '',
  branch_id: '' as string,
  search: '' as string,
  page: 1,
  size: 20,
})

const branches = ref<Array<{ id: string; name: string }>>([])
const branchOptions = computed(() => branches.value.map(b => ({ id: b.id, label: b.name })))

const STATUS_OPTIONS = [
  { id: 'draft',     label: CONTRACT_STATUS.draft },
  { id: 'signed',    label: CONTRACT_STATUS.signed },
  { id: 'cancelled', label: CONTRACT_STATUS.cancelled },
  { id: 'completed', label: CONTRACT_STATUS.completed },
]
const PAYMENT_STATUS_OPTIONS = [
  { id: 'paid',    label: "To'liq to'langan" },
  { id: 'partial', label: "Qisman to'langan" },
  { id: 'unpaid',  label: "To'lanmagan" },
]

async function load() {
  loading.value = true
  try {
    const res = await contractsApi.listDetailed({
      status: filters.status || undefined,
      payment_status: filters.payment_status || undefined,
      branch_id: filters.branch_id || undefined,
      search: filters.search || undefined,
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

let searchT: ReturnType<typeof setTimeout> | null = null
watch(() => filters.search, () => {
  if (searchT) clearTimeout(searchT)
  searchT = setTimeout(() => { filters.page = 1; load() }, 300)
})
watch(() => [filters.status, filters.payment_status, filters.branch_id], () => {
  filters.page = 1; load()
})
watch(() => filters.page, load)

onMounted(async () => {
  branches.value = await adminApi.branches.list(false).catch(() => [])
  // Hydrate from URL query so links like
  // /accountant/contracts?payment_status=unpaid land on the filtered view.
  const q = route.query
  if (typeof q.payment_status === 'string' && ['paid', 'partial', 'unpaid'].includes(q.payment_status)) {
    filters.payment_status = q.payment_status as PaymentStatusFilter
  }
  if (typeof q.status === 'string') filters.status = q.status as ContractStatus
  if (typeof q.branch_id === 'string') filters.branch_id = q.branch_id
  if (typeof q.search === 'string') filters.search = q.search
  await load()
})

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

const activeFilterCount = computed(() => {
  let n = 0
  if (filters.status) n++
  if (filters.payment_status) n++
  if (filters.branch_id) n++
  return n
})

function clearFilters() {
  filters.status = ''
  filters.payment_status = ''
  filters.branch_id = ''
  filters.search = ''
}

function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '0'
  return Math.round(n).toLocaleString('uz-UZ')
}

function paymentTone(item: ContractListItem) {
  const total = Number(item.total_amount) || 0
  const paid = Number(item.paid_amount) || 0
  if (paid >= total && total > 0) return 'paid'
  if (paid > 0) return 'partial'
  return 'unpaid'
}

function paymentLabel(item: ContractListItem) {
  const t = paymentTone(item)
  return t === 'paid' ? "To'liq" : t === 'partial' ? "Qisman" : "To'lanmagan"
}

function progressPercent(item: ContractListItem) {
  const total = Number(item.total_amount) || 0
  const paid = Number(item.paid_amount) || 0
  if (total <= 0) return 0
  return Math.min(100, Math.round((paid / total) * 100))
}

const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    await downloadCsv('/contracts/export.csv', {
      status: filters.status || undefined,
      payment_status: filters.payment_status || undefined,
      branch_id: filters.branch_id || undefined,
      search: filters.search || undefined,
    })
    toast.success("CSV yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Shartnomalar"
      :subtitle="`Jami ${total} ta · To'lov holati va qoldiqlarni boshqaring`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/accountant' }, { label: 'Shartnomalar' }]"
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
        <button v-if="activeFilterCount || filters.search"
                class="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1"
                @click="clearFilters">
          <XIcon class="w-3 h-3" /> Tozalash
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="lg:col-span-2">
          <label class="field-label">Qidirish</label>
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input v-model="filters.search" class="input pl-10" placeholder="Shartnoma № yoki F.I.Sh." />
          </div>
        </div>
        <div>
          <label class="field-label">To'lov holati</label>
          <SearchSelect v-model="filters.payment_status" :options="PAYMENT_STATUS_OPTIONS" placeholder="— hammasi —" allow-clear />
        </div>
        <div>
          <label class="field-label">Filial</label>
          <SearchSelect v-model="filters.branch_id" :options="branchOptions" placeholder="— hammasi —" allow-clear />
        </div>
      </div>
    </div>

    <!-- Quick payment-status tiles -->
    <div class="grid grid-cols-3 gap-2 mb-4">
      <button type="button"
              class="text-left rounded-xl px-3 py-2.5 border bg-white dark:bg-slate-900 hover:shadow-sm transition"
              :class="filters.payment_status === '' ? 'border-brand-300 ring-2 ring-brand-200/60 dark:border-brand-600 dark:ring-brand-700/30' : 'border-slate-200/70 dark:border-slate-800'"
              @click="filters.payment_status = ''">
        <div class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Hammasi</div>
      </button>
      <button type="button"
              class="text-left rounded-xl px-3 py-2.5 border bg-white dark:bg-slate-900 hover:shadow-sm transition"
              :class="filters.payment_status === 'unpaid' ? 'border-rose-400 ring-2 ring-rose-300/60' : 'border-slate-200/70 dark:border-slate-800'"
              @click="filters.payment_status = filters.payment_status === 'unpaid' ? '' : 'unpaid'">
        <div class="text-[10px] uppercase tracking-wider text-rose-700 dark:text-rose-300 font-semibold inline-flex items-center gap-1">
          <AlertTriangle class="w-3 h-3" /> To'lanmagan
        </div>
      </button>
      <button type="button"
              class="text-left rounded-xl px-3 py-2.5 border bg-white dark:bg-slate-900 hover:shadow-sm transition"
              :class="filters.payment_status === 'partial' ? 'border-amber-400 ring-2 ring-amber-300/60' : 'border-slate-200/70 dark:border-slate-800'"
              @click="filters.payment_status = filters.payment_status === 'partial' ? '' : 'partial'">
        <div class="text-[10px] uppercase tracking-wider text-amber-700 dark:text-amber-300 font-semibold inline-flex items-center gap-1">
          <Clock class="w-3 h-3" /> Qisman
        </div>
      </button>
    </div>

    <Skeleton v-if="loading" type="table" />
    <div v-else-if="!items.length" class="card p-6">
      <EmptyState :icon="FileText" title="Shartnomalar topilmadi" subtitle="Filtrlarni tozalang yoki keyinroq qayting" />
    </div>

    <!-- Mobile card list (< md) -->
    <ul v-else class="md:hidden space-y-2.5">
      <li v-for="c in items" :key="c.id" class="card p-4">
        <div class="flex items-start justify-between gap-2 mb-2">
          <div class="min-w-0">
            <div class="font-semibold text-slate-900 dark:text-slate-100 break-words">{{ c.applicant_full_name || '—' }}</div>
            <div class="font-mono text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{{ c.contract_number }}</div>
          </div>
          <StatusBadge :status="c.status" :label="tr(CONTRACT_STATUS, c.status)" />
        </div>
        <div class="text-xs text-slate-600 dark:text-slate-400 mb-2 truncate">
          {{ c.program_name || '—' }}<span v-if="c.branch_name" class="text-slate-400 dark:text-slate-500"> · {{ c.branch_name }}</span>
        </div>
        <div class="text-xs flex items-center justify-between gap-2 mb-1">
          <span>{{ fmtMoney(c.paid_amount) }} / {{ fmtMoney(c.total_amount) }} {{ c.currency }}</span>
          <span class="font-bold tabular-nums"
                :class="paymentTone(c) === 'paid' ? 'text-emerald-600 dark:text-emerald-400'
                      : paymentTone(c) === 'partial' ? 'text-amber-600 dark:text-amber-400'
                      : 'text-rose-600 dark:text-rose-400'">
            {{ paymentLabel(c) }}
          </span>
        </div>
        <div class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div class="h-full transition-all"
               :class="paymentTone(c) === 'paid' ? 'bg-emerald-500'
                     : paymentTone(c) === 'partial' ? 'bg-amber-500'
                     : 'bg-rose-500'"
               :style="{ width: progressPercent(c) + '%' }"></div>
        </div>
        <div class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center gap-2">
          <RouterLink :to="`/accountant/contracts/${c.id}`"
                      class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">
            <Eye class="w-3.5 h-3.5" /> Shartnoma
          </RouterLink>
          <RouterLink :to="`/accountant/contracts/${c.id}/payments`"
                      class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-brand-600 text-white">
            <CreditCard class="w-3.5 h-3.5" /> To'lovlar
          </RouterLink>
        </div>
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
              <th class="text-left font-semibold px-5 py-3.5">Shartnoma</th>
              <th class="text-left font-semibold px-4 py-3.5">F.I.Sh.</th>
              <th class="text-left font-semibold px-4 py-3.5">Yo'nalish / Filial</th>
              <th class="text-left font-semibold px-4 py-3.5 w-44">To'lov</th>
              <th class="text-left font-semibold px-4 py-3.5 w-32">Holati</th>
              <th class="text-right font-semibold px-5 py-3.5 w-28">Amal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in items" :key="c.id"
                class="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors cursor-pointer group"
                @click="router.push(`/accountant/contracts/${c.id}/payments`)">
              <td class="px-5 py-4">
                <div class="font-mono text-xs font-semibold text-slate-900 dark:text-slate-100 group-hover:text-brand-700 dark:group-hover:text-brand-300 transition-colors">{{ c.contract_number }}</div>
                <div v-if="c.signed_at" class="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                  Imzo: {{ new Date(c.signed_at).toLocaleDateString('uz-UZ') }}
                </div>
              </td>
              <td class="px-4 py-4 min-w-[18ch]">
                <!-- Full F.I.Sh., no clamp. Accountants compared their list
                     against the bank's deposit slip and Uzbek triple-barrel
                     names ("ABDIRAHMONOVA NIGORAXON SHUKHRATBEKOVNA") were
                     getting cut off — they couldn't tell two students apart
                     without hovering. break-words keeps long names from
                     pushing the page wider than the viewport. -->
                <div class="text-sm font-medium text-slate-900 dark:text-slate-100 break-words leading-snug">{{ c.applicant_full_name || '—' }}</div>
              </td>
              <td class="px-4 py-4 min-w-[22ch]">
                <div class="text-sm text-slate-700 dark:text-slate-300 break-words leading-snug">{{ c.program_name || '—' }}</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 break-words leading-snug mt-0.5">{{ c.branch_name || '—' }}</div>
              </td>
              <td class="px-4 py-4">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-xs font-semibold tabular-nums"
                        :class="paymentTone(c) === 'paid' ? 'text-emerald-600 dark:text-emerald-400'
                              : paymentTone(c) === 'partial' ? 'text-amber-600 dark:text-amber-400'
                              : 'text-rose-600 dark:text-rose-400'">
                    {{ progressPercent(c) }}%
                  </span>
                  <span class="text-[11px] text-slate-500 dark:text-slate-400 tabular-nums">
                    {{ fmtMoney(c.paid_amount) }} / {{ fmtMoney(c.total_amount) }}
                  </span>
                </div>
                <div class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div class="h-full transition-all"
                       :class="paymentTone(c) === 'paid' ? 'bg-emerald-500'
                             : paymentTone(c) === 'partial' ? 'bg-amber-500'
                             : 'bg-rose-500'"
                       :style="{ width: progressPercent(c) + '%' }"></div>
                </div>
                <div v-if="paymentTone(c) !== 'paid'" class="text-[10px] text-rose-600 dark:text-rose-400 mt-1 inline-flex items-center gap-1">
                  <AlertTriangle class="w-2.5 h-2.5" /> Qoldiq: {{ fmtMoney(c.balance) }} {{ c.currency }}
                </div>
              </td>
              <td class="px-4 py-4">
                <StatusBadge :status="c.status" :label="tr(CONTRACT_STATUS, c.status)" />
              </td>
              <td class="px-5 py-4 text-right" @click.stop>
                <div class="inline-flex items-center gap-1.5">
                  <RouterLink :to="`/accountant/contracts/${c.id}`" class="btn-outline btn-sm" title="Shartnoma + PDF">
                    <Eye class="w-3.5 h-3.5" /> Ko'rish
                  </RouterLink>
                  <RouterLink :to="`/accountant/contracts/${c.id}/payments`" class="btn-outline btn-sm">
                    <ArrowRight class="w-3.5 h-3.5" /> To'lovlar
                  </RouterLink>
                </div>
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
