<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { CreditCard, CheckCircle2, XCircle, RotateCcw, Download } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi } from '@/api/admin.api'
import { downloadCsv } from '@/api/http'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { PAYMENT_STATUS, tr } from '@/utils/labels'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'
import { useBulkSelect } from '@/composables/useBulkSelect'
import BulkActionBar from '@/components/ui/BulkActionBar.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

interface Payment {
  id: string
  payment_number: string
  contract_id: string
  amount: string
  currency: string
  status: string
  reference?: string | null
  paid_at?: string | null
  failed_reason?: string | null
  created_at: string
}

const toast = useToast()
const route = useRoute()
const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')
const { ask } = useConfirm()
const auth = useAuthStore()

const items = ref<Payment[]>([])
const total = ref(0)
const loading = ref(false)
const filters = reactive({ status: '', page: 1, size: 20 })

const bulk = useBulkSelect<Payment>(() => items.value)
const bulkBusy = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await adminApi.payments.list({
      status: filters.status || undefined,
      // Operator panel: only payments this operator logged. Other panels
      // (admin, accountant) see the full list.
      registered_by_id: isOperatorPanel.value && auth.user?.id ? auth.user.id : undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items as Payment[]
    total.value = res.total
    bulk.clear()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

watch(() => filters.status, () => { filters.page = 1; load() })
watch(() => filters.page, load)
onMounted(load)

async function confirm(p: Payment) {
  const reference = window.prompt("Tasdiqlash uchun reference (chek raqami):") || ''
  if (!reference) return
  try {
    await adminApi.payments.confirm(p.id, { reference })
    toast.success("Tasdiqlandi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function fail(p: Payment) {
  const reason = window.prompt("Sabab:") || ''
  const ok = await ask({
    title: "Bajarilmagan deb belgilash",
    message: `${p.payment_number} bajarilmagan deb belgilansinmi?`,
    confirmLabel: "Tasdiqlash",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.payments.fail(p.id, reason)
    toast.success("Belgilandi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function refund(p: Payment) {
  const reason = window.prompt("Qaytarish sababi:") || ''
  const ok = await ask({
    title: "Qaytarish",
    message: `${p.payment_number} qaytarilsinmi?`,
    confirmLabel: "Qaytarish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.payments.refund(p.id, reason)
    toast.success("Qaytarildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    await downloadCsv('/payments/export.csv', { status: filters.status || undefined })
    toast.success("CSV yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}

async function bulkConfirmSelected() {
  const ids = bulk.selectedIds.value
  if (!ids.length) return
  const ok = await ask({
    title: `${ids.length} ta to'lov tasdiqlansinmi?`,
    message: "Statusi 'pending' bo'lgan to'lovlar tasdiqlanadi. Boshqalari o'tkazib yuboriladi.",
    confirmLabel: 'Tasdiqlash',
    tone: 'primary',
  })
  if (!ok) return
  bulkBusy.value = true
  try {
    const res = await adminApi.payments.bulkConfirm(ids)
    toast.success(`${res.confirmed} ta tasdiqlandi${res.skipped ? `, ${res.skipped} ta o'tkazib yuborildi` : ''}`)
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string }; detail?: string }>
    toast.error(ax.response?.data?.error?.message || ax.response?.data?.detail || "Xatolik")
  } finally {
    bulkBusy.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="To'lovlar"
      :subtitle="`Shartnoma bo'yicha qabul qilingan to'lovlar · Jami ${total}`"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'Qabul jarayoni' }]"
    >
      <button class="btn-outline" :disabled="exporting" @click="exportCsv">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'CSV' }}
      </button>
    </PageHeader>


    <div class="filter-bar">
      <div class="min-w-[200px]">
        <label class="field-label">Holati</label>
        <select v-model="filters.status" class="input">
          <option value="">Hammasi</option>
          <option value="pending">{{ PAYMENT_STATUS.pending }}</option>
          <option value="confirmed">{{ PAYMENT_STATUS.confirmed }}</option>
          <option value="failed">{{ PAYMENT_STATUS.failed }}</option>
          <option value="refunded">{{ PAYMENT_STATUS.refunded }}</option>
        </select>
      </div>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th class="w-8 px-3">
              <input type="checkbox" class="rounded cursor-pointer"
                     :checked="bulk.allSelected.value"
                     :indeterminate.prop="bulk.partial.value"
                     @change="bulk.toggleAll()" />
            </th>
            <th>To'lov №</th>
            <th class="w-44">Summa</th>
            <th>Reference</th>
            <th class="w-32">Sana</th>
            <th class="w-32">Holati</th>
            <th class="w-40 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="i in 6" :key="`sk-row-${i}`" class="border-b border-slate-100 dark:border-slate-800/60">
              <td v-for="c in 6" :key="`sk-${i}-${c}`" class="px-5 py-4">
                <div class="skeleton h-3 rounded" :class="c === 1 ? 'w-3/4' : 'w-1/2'" />
              </td>
            </tr>
          </template>
          <tr v-else-if="!items.length">
            <td colspan="6" class="p-0">
              <EmptyState :icon="CreditCard" title="To'lovlar yo'q" />
            </td>
          </tr>
          <tr v-for="p in items" :key="p.id"
              :class="bulk.isSelected(p.id) ? 'bg-brand-50/40 dark:bg-brand-500/10' : ''">
            <td class="px-3">
              <input type="checkbox" class="rounded cursor-pointer"
                     :checked="bulk.isSelected(p.id)"
                     @change="bulk.toggle(p.id)" />
            </td>
            <td class="font-mono text-xs text-slate-600 dark:text-slate-300">{{ p.payment_number }}</td>
            <td class="text-slate-900 dark:text-slate-100 font-medium">
              {{ Number(p.amount).toLocaleString('uz-UZ') }}
              <span class="text-xs text-slate-500 dark:text-slate-400 ml-1">{{ p.currency }}</span>
            </td>
            <td class="text-xs text-slate-600 dark:text-slate-400 font-mono">{{ p.reference || '—' }}</td>
            <td class="text-xs text-slate-600 dark:text-slate-400">
              {{ p.paid_at ? new Date(p.paid_at).toLocaleDateString('uz-UZ') : '—' }}
            </td>
            <td><StatusBadge :status="p.status" :label="tr(PAYMENT_STATUS, p.status)" /></td>
            <td class="text-right">
              <div v-if="!isOperatorPanel" class="inline-flex items-center gap-1">
                <button v-if="p.status === 'pending'"
                        class="icon-btn !text-emerald-600 hover:!bg-emerald-50 dark:hover:!bg-emerald-900/30"
                        title="Tasdiqlash" @click="confirm(p)">
                  <CheckCircle2 class="w-4 h-4" />
                </button>
                <button v-if="p.status === 'pending'"
                        class="icon-btn !text-amber-600 hover:!bg-amber-50 dark:hover:!bg-amber-900/30"
                        title="Bajarilmagan" @click="fail(p)">
                  <XCircle class="w-4 h-4" />
                </button>
                <button v-if="p.status === 'confirmed'"
                        class="icon-btn !text-rose-600 hover:!bg-rose-50 dark:hover:!bg-rose-900/30"
                        title="Qaytarish" @click="refund(p)">
                  <RotateCcw class="w-4 h-4" />
                </button>
              </div>
              <span v-else class="text-xs text-slate-400">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="items.length" class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">Sahifa {{ filters.page }} / {{ lastPage() }}</div>
        <div class="flex gap-2">
          <button class="btn-ghost" :disabled="filters.page <= 1" @click="filters.page--">‹</button>
          <button class="btn-ghost" :disabled="filters.page >= lastPage()" @click="filters.page++">›</button>
        </div>
      </div>
    </div>

    <BulkActionBar :count="bulk.count.value"
                   :label="`${bulk.count.value} ta to'lov tanlandi`"
                   @clear="bulk.clear()">
      <button type="button"
              class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white transition disabled:opacity-50"
              :disabled="bulkBusy"
              @click="bulkConfirmSelected">
        Tasdiqlash
      </button>
    </BulkActionBar>
  </div>
</template>
