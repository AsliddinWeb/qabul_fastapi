<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { FileText, FileSignature, Ban, Download } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi } from '@/api/admin.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { CONTRACT_STATUS, CONTRACT_TYPE, tr } from '@/utils/labels'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'
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
}

const toast = useToast()
const route = useRoute()
const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')
const { ask } = useConfirm()
const auth = useAuthStore()

const items = ref<Contract[]>([])
const total = ref(0)
const loading = ref(false)
const filters = reactive({
  status: '' as string,
  type: '' as string,
  search: '' as string,
  page: 1,
  size: 20,
})

async function load() {
  loading.value = true
  try {
    const res = await adminApi.contracts.list({
      status: filters.status || undefined,
      type: filters.type || undefined,
      // On the operator panel, only show contracts this operator issued.
      // Admin/accountant view the full list.
      created_by_id: isOperatorPanel.value && auth.user?.id ? auth.user.id : undefined,
      search: filters.search || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items as Contract[]
    total.value = res.total
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
watch(() => filters.page, load)
onMounted(load)

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
      <div class="flex-1 min-w-[200px]">
        <label class="field-label">Shartnoma raqami</label>
        <input v-model="filters.search" class="input font-mono" placeholder="C-2026-..." />
      </div>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Shartnoma №</th>
            <th class="w-32">Turi</th>
            <th class="w-44">Summa</th>
            <th class="w-32">Imzolangan</th>
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
              <EmptyState :icon="FileText" title="Shartnomalar yo'q" />
            </td>
          </tr>
          <tr v-for="c in items" :key="c.id">
            <td class="font-mono text-xs text-slate-600 dark:text-slate-300">{{ c.contract_number }}</td>
            <td class="text-xs">{{ tr(CONTRACT_TYPE, c.type) }}</td>
            <td class="text-slate-900 dark:text-slate-100">
              <span class="font-medium">{{ Number(c.total_amount).toLocaleString('uz-UZ') }}</span>
              <span class="text-xs text-slate-500 dark:text-slate-400 ml-1">{{ c.currency }}</span>
              <div class="text-xs text-slate-500 dark:text-slate-400">
                to'langan: {{ Number(c.paid_amount).toLocaleString('uz-UZ') }}
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
      <div v-if="items.length" class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">Sahifa {{ filters.page }} / {{ lastPage() }}</div>
        <div class="flex gap-2">
          <button class="btn-ghost" :disabled="filters.page <= 1" @click="filters.page--">‹</button>
          <button class="btn-ghost" :disabled="filters.page >= lastPage()" @click="filters.page++">›</button>
        </div>
      </div>
    </div>
  </div>
</template>
