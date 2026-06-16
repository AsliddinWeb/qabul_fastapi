<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileText, FileSignature, Ban, Download } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi } from '@/api/admin.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { CONTRACT_STATUS, CONTRACT_TYPE, tr } from '@/utils/labels'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'
import { useBulkSelect } from '@/composables/useBulkSelect'
import BulkActionBar from '@/components/ui/BulkActionBar.vue'
import Pagination from '@/components/ui/Pagination.vue'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

interface Contract {
  id: string
  contract_number: string
  application_id: string
  type: string
  total_amount: string
  paid_amount: string
  currency: string
  status: string
  signed_at: string | null
  pdf_file_id: string | null
  created_at: string
  // Joined fields from backend list_detailed
  applicant_full_name?: string | null
  branch_name?: string | null
  program_name?: string | null
  balance?: string | null
}

const toast = useToast()
const route = useRoute()
const router = useRouter()
const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')
const { ask } = useConfirm()
const auth = useAuthStore()

const items = ref<Contract[]>([])
const total = ref(0)
const loading = ref(false)

const bulk = useBulkSelect<Contract>(() => items.value)
const bulkBusy = ref(false)
const filters = reactive({
  status: '' as string,
  type: '' as string,
  created_by_id: '' as string,
  search: '' as string,
  page: 1,
  size: 20,
})

// Operator pool for the "Operator" filter. Only admins / superadmins
// have users.list permission — operators don't, so skip the fetch
// (would 403) and hide the dropdown for them.
const canListOperators = computed(() => auth.hasPermission('users.list'))
const operatorOptions = ref<Array<{ id: string; label: string }>>([])
async function loadOperators() {
  if (!canListOperators.value) return
  try {
    const us = await adminApi.users.list({ role: 'operator', size: 100 }).catch(() => null)
    if (us) {
      operatorOptions.value = us.items.map(u => ({
        id: u.id,
        label: u.full_name || u.phone || u.id.slice(0, 8),
      }))
    }
  } catch { /* ignore */ }
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.contracts.list({
      status: filters.status || undefined,
      type: filters.type || undefined,
      // Phase 2: full visibility on every staff panel. Use the Operator
      // filter (added below) to scope to "mine" or a colleague's work.
      created_by_id: filters.created_by_id || undefined,
      search: filters.search || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items as Contract[]
    total.value = res.total
    bulk.clear()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(() => filters.search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { filters.page = 1; load() }, 300)
})
watch(() => filters.status, () => { filters.page = 1; load() })
watch(() => filters.type, () => { filters.page = 1; load() })
watch(() => filters.created_by_id, () => { filters.page = 1; load() })
watch(() => filters.page, load)
onMounted(() => Promise.all([load(), loadOperators()]))

async function sign(c: Contract) {
  const ok = await ask({
    title: "Shartnomani imzolash",
    message: `${c.contract_number} imzolanganligi tasdiqlansinmi?`,
    confirmLabel: "Imzolash",
    tone: 'primary',
  })
  if (!ok) return
  try {
    await adminApi.contracts.sign(c.id)
    toast.success("Imzolandi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function cancel(c: Contract) {
  const ok = await ask({
    title: "Shartnomani bekor qilish",
    message: `${c.contract_number} bekor qilinsinmi?`,
    confirmLabel: "Bekor qilish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.contracts.cancel(c.id)
    toast.success("Bekor qilindi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

async function bulkCancelSelected() {
  const ids = bulk.selectedIds.value
  if (!ids.length) return
  const ok = await ask({
    title: `${ids.length} ta shartnoma bekor qilinsinmi?`,
    message: "Shartnomalarning statusi 'cancelled' ga o'tadi. Hard delete amalga oshirilmaydi — to'lov va audit tarixi saqlanib qoladi.",
    confirmLabel: 'Bekor qilish',
    tone: 'danger',
  })
  if (!ok) return
  bulkBusy.value = true
  try {
    const res = await adminApi.contracts.bulkCancel(ids)
    toast.success(`${res.cancelled} ta bekor qilindi${res.skipped ? `, ${res.skipped} ta o'tkazib yuborildi` : ''}`)
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
      title="Shartnomalar"
      :subtitle="`Universitet bilan tuzilgan shartnomalar · Jami ${total}`"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'Qabul jarayoni' }]"
    />


    <div class="filter-bar">
      <div class="min-w-[180px]">
        <label class="field-label">Holati</label>
        <select v-model="filters.status" class="input">
          <option value="">Hammasi</option>
          <option value="draft">{{ CONTRACT_STATUS.draft }}</option>
          <option value="signed">{{ CONTRACT_STATUS.signed }}</option>
          <option value="cancelled">{{ CONTRACT_STATUS.cancelled }}</option>
          <option value="completed">{{ CONTRACT_STATUS.completed }}</option>
        </select>
      </div>
      <div class="min-w-[180px]">
        <label class="field-label">Turi</label>
        <select v-model="filters.type" class="input">
          <option value="">Hammasi</option>
          <option value="two_party">{{ CONTRACT_TYPE.two_party }}</option>
          <option value="three_party">{{ CONTRACT_TYPE.three_party }}</option>
        </select>
      </div>
      <div v-if="canListOperators" class="min-w-[200px]">
        <label class="field-label">Operator</label>
        <SearchSelect v-model="filters.created_by_id" :options="operatorOptions" placeholder="— hammasi —" allow-clear />
      </div>
      <div class="flex-1 min-w-[220px]">
        <label class="field-label">Qidirish</label>
        <input v-model="filters.search" class="input" placeholder="Shartnoma №, F.I.Sh., yo'nalish..." />
      </div>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th v-if="!isOperatorPanel" class="w-8 px-3">
              <input type="checkbox" class="rounded cursor-pointer"
                     :checked="bulk.allSelected.value"
                     :indeterminate.prop="bulk.partial.value"
                     @change="bulk.toggleAll()" />
            </th>
            <th class="w-40">Shartnoma №</th>
            <th>F.I.Sh.</th>
            <th>Yo'nalish</th>
            <th class="w-32">Filial</th>
            <th class="w-28">Turi</th>
            <th class="w-44">Summa / Balans</th>
            <th class="w-28">Imzolangan</th>
            <th class="w-28">Holati</th>
            <th class="w-32 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="i in 6" :key="`sk-row-${i}`" class="border-b border-slate-100 dark:border-slate-800/60">
              <td v-for="c in 9" :key="`sk-${i}-${c}`" class="px-5 py-4">
                <div class="skeleton h-3 rounded" :class="c === 2 ? 'w-3/4' : 'w-1/2'" />
              </td>
            </tr>
          </template>
          <tr v-else-if="!items.length">
            <td colspan="9" class="p-0">
              <EmptyState :icon="FileText" title="Shartnomalar yo'q" />
            </td>
          </tr>
          <tr v-for="c in items" :key="c.id"
              class="cursor-pointer"
              :class="bulk.isSelected(c.id) ? 'bg-brand-50/40 dark:bg-brand-500/10' : ''"
              @click="router.push(`${panelPrefix}/contracts/${c.id}`)">
            <td v-if="!isOperatorPanel" class="px-3" @click.stop>
              <input type="checkbox" class="rounded cursor-pointer"
                     :checked="bulk.isSelected(c.id)"
                     @change="bulk.toggle(c.id)" />
            </td>
            <td class="font-mono text-xs text-slate-600 dark:text-slate-300">{{ c.contract_number }}</td>
            <td class="text-slate-900 dark:text-slate-100 font-medium break-words leading-snug min-w-[18ch]">
              {{ c.applicant_full_name || '—' }}
            </td>
            <td class="text-xs text-slate-700 dark:text-slate-300 break-words leading-snug min-w-[20ch]">
              {{ c.program_name || '—' }}
            </td>
            <td class="text-xs text-slate-600 dark:text-slate-400 break-words leading-snug min-w-[14ch]">
              {{ c.branch_name || '—' }}
            </td>
            <td class="text-xs"><span class="pill">{{ tr(CONTRACT_TYPE, c.type) }}</span></td>
            <td class="text-slate-900 dark:text-slate-100">
              <div class="text-sm font-medium tabular-nums">{{ Number(c.total_amount).toLocaleString('uz-UZ') }}</div>
              <div class="text-[10px] text-slate-500 dark:text-slate-400 tabular-nums">
                <span class="text-emerald-600 dark:text-emerald-400">{{ Number(c.paid_amount).toLocaleString('uz-UZ') }}</span>
                <template v-if="Number(c.balance ?? (Number(c.total_amount) - Number(c.paid_amount))) > 0">
                  · qarz <span class="text-rose-600 dark:text-rose-400">{{ Number(c.balance ?? (Number(c.total_amount) - Number(c.paid_amount))).toLocaleString('uz-UZ') }}</span>
                </template>
              </div>
            </td>
            <td class="text-xs text-slate-600 dark:text-slate-400">
              {{ c.signed_at ? new Date(c.signed_at).toLocaleDateString('uz-UZ') : '—' }}
            </td>
            <td><StatusBadge :status="c.status" :label="tr(CONTRACT_STATUS, c.status)" /></td>
            <td class="text-right">
              <div class="inline-flex gap-1">
                <button v-if="c.pdf_file_id && c.signed_at"
                        type="button"
                        class="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800" title="PDF yuklab olish"
                        @click="adminApi.contracts.openPdf(c.id)">
                  <Download class="w-4 h-4 text-slate-500" />
                </button>
                <button v-if="c.status === 'draft'"
                        class="p-1.5 rounded hover:bg-green-100 dark:hover:bg-green-900/30" title="Imzolash"
                        @click="sign(c)">
                  <FileSignature class="w-4 h-4 text-green-600" />
                </button>
                <button v-if="!isOperatorPanel && c.status !== 'cancelled' && c.status !== 'completed'"
                        class="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30" title="Bekor qilish"
                        @click="cancel(c)">
                  <Ban class="w-4 h-4 text-red-600" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <Pagination v-if="items.length" v-model:page="filters.page" :last-page="lastPage()" :total="total" :size="filters.size" />
    </div>

    <BulkActionBar v-if="!isOperatorPanel"
                   :count="bulk.count.value"
                   :label="`${bulk.count.value} ta shartnoma tanlandi`"
                   @clear="bulk.clear()">
      <button type="button"
              class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition disabled:opacity-50"
              :disabled="bulkBusy"
              @click="bulkCancelSelected">
        Bekor qilish
      </button>
    </BulkActionBar>
  </div>
</template>
