<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Download, FileText, CheckCircle2, Clock, XCircle,
  Building2, User, Wallet, AlertTriangle,
} from 'lucide-vue-next'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import { paymentsApi, type PaymentRead } from '@/api/payments.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { CONTRACT_STATUS, CONTRACT_TYPE, PAYMENT_STATUS, tr } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const contract = ref<ContractDetailed | null>(null)
const payments = ref<PaymentRead[]>([])
const loading = ref(true)
const downloading = ref(false)

onMounted(async () => {
  try {
    const list = await contractsApi.myList()
    contract.value = list.find((c) => c.id === id.value) || null
    if (contract.value) {
      const all = await paymentsApi.myList().catch(() => [])
      payments.value = all.filter((p) => p.contract_id === id.value)
    }
  } finally { loading.value = false }
})

async function downloadPdf() {
  if (!contract.value) return
  downloading.value = true
  try { await contractsApi.openPdf(contract.value.id) }
  finally { downloading.value = false }
}

function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!n || isNaN(n)) return '—'
  return Number(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}
function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

const PAYMENT_TONE: Record<string, string> = {
  pending:   'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  confirmed: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
  failed:    'bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
  refunded:  'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}
const PAYMENT_ICON: Record<string, any> = {
  pending: Clock, confirmed: CheckCircle2, failed: XCircle, refunded: Wallet,
}

const totalAmount = computed(() => parseFloat(contract.value?.total_amount || '0'))
const paidAmount  = computed(() => parseFloat(contract.value?.paid_amount  || '0'))
const remaining   = computed(() => Math.max(0, totalAmount.value - paidAmount.value))
const paidPercent = computed(() => totalAmount.value
  ? Math.min(100, Math.round((paidAmount.value / totalAmount.value) * 100))
  : 0)

const PARTY_LABELS: Record<string, string> = {
  university: 'Universitet',
  student:    'Talaba',
  sponsor:    'Homiy',
  parent:     'Ota-ona',
}
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="!contract">
    <PageHeader
      title="Shartnoma topilmadi"
      :crumbs="[{ label: 'Bosh sahifa', to: '/applicant' }, { label: 'Shartnomalarim', to: '/applicant/contracts' }]"
    >
      <button class="btn-ghost" @click="router.push('/applicant/contracts')">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>
    <div class="card p-12 text-center text-slate-500">
      Bu shartnoma sizniki emas yoki mavjud emas.
    </div>
  </div>

  <div v-else class="space-y-6">
    <PageHeader
      :title="`Shartnoma ${contract.contract_number}`"
      :subtitle="`${tr(CONTRACT_TYPE, contract.type)} · ${fmtMoney(contract.total_amount)} ${contract.currency}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/applicant' }, { label: 'Shartnomalarim', to: '/applicant/contracts' }]"
    >
      <StatusBadge :status="contract.status" :label="tr(CONTRACT_STATUS, contract.status)" />
      <button class="btn-primary" :disabled="downloading || !contract.pdf_file_id" @click="downloadPdf">
        <Download class="w-4 h-4" />
        {{ downloading ? '...' : 'PDF yuklab olish' }}
      </button>
    </PageHeader>

    <!-- Cancelled banner -->
    <div v-if="contract.status === 'cancelled'"
         class="card p-5 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-700/30 flex items-start gap-3">
      <AlertTriangle class="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
      <div>
        <div class="font-semibold text-rose-900 dark:text-rose-200">Shartnoma bekor qilingan</div>
        <p class="text-sm text-rose-800 dark:text-rose-300 mt-0.5">
          Bu shartnoma kuchsiz. Yangi shartnoma uchun operator bilan bog'laning.
        </p>
      </div>
    </div>

    <!-- Payment summary -->
    <section class="card p-6 sm:p-7">
      <div class="flex items-center justify-between mb-4">
        <h2 class="font-bold text-lg text-slate-900 dark:text-slate-100">To'lov holati</h2>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Jami</div>
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">
            {{ fmtMoney(totalAmount) }}
          </div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">To'langan</div>
          <div class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
            {{ fmtMoney(paidAmount) }}
          </div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Qoldiq</div>
          <div class="text-2xl font-bold tabular-nums"
               :class="remaining > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'">
            {{ fmtMoney(remaining) }}
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1.5">
        <span>To'lov darajasi</span>
        <span class="font-mono font-bold">{{ paidPercent }}%</span>
      </div>
      <div class="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
        <div class="h-full rounded-full bg-emerald-500 transition-all"
             :style="{ width: paidPercent + '%' }"></div>
      </div>

      <!-- IMPORTANT: NO online to'lov button. Read-only history below. -->
      <div class="mt-5 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-xs text-slate-600 dark:text-slate-400 flex items-start gap-2.5">
        <Wallet class="w-4 h-4 shrink-0 mt-0.5" />
        <div>
          To'lovlar offline amalga oshiriladi. Bank, Click, Payme yoki kassa orqali to'lagandan so'ng,
          buxgalter to'lovni tasdiqlaydi va bu yerda ko'rinadi.
        </div>
      </div>
    </section>

    <!-- Payment history -->
    <section v-if="payments.length" class="card p-6 sm:p-7">
      <h2 class="font-bold text-lg mb-4 text-slate-900 dark:text-slate-100">
        To'lov tarixi
        <span class="text-sm font-normal text-slate-500 ml-1">({{ payments.length }})</span>
      </h2>

      <ul class="divide-y divide-slate-100 dark:divide-slate-800">
        <li v-for="p in payments" :key="p.id"
            class="py-4 flex items-center gap-4 first:pt-0 last:pb-0">
          <span class="grid place-items-center w-10 h-10 rounded-xl shrink-0"
                :class="PAYMENT_TONE[p.status]">
            <component :is="PAYMENT_ICON[p.status] || Wallet" class="w-4 h-4" />
          </span>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-mono text-xs text-slate-500 dark:text-slate-400">{{ p.payment_number }}</span>
            </div>
            <div class="text-base font-bold text-slate-900 dark:text-slate-100 tabular-nums mt-0.5">
              {{ fmtMoney(p.amount) }}
              <span class="text-xs font-normal text-slate-500">{{ p.currency }}</span>
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {{ p.paid_at ? fmtDate(p.paid_at) : "Tasdiqlanmagan" }}
            </div>
          </div>
          <StatusBadge :status="p.status" :label="tr(PAYMENT_STATUS, p.status)" />
        </li>
      </ul>
    </section>

    <!-- Parties -->
    <section class="card p-6 sm:p-7">
      <h2 class="font-bold text-lg mb-4 text-slate-900 dark:text-slate-100">Tomonlar</h2>
      <ul class="divide-y divide-slate-100 dark:divide-slate-800">
        <li v-for="p in contract.parties" :key="p.id" class="py-4 flex items-start gap-4 first:pt-0 last:pb-0">
          <span class="grid place-items-center w-10 h-10 rounded-xl shrink-0"
                :style="{
                  background: p.party_role === 'university' ? 'rgb(238 242 255)' :
                              p.party_role === 'student'    ? 'rgb(255 251 235)' :
                                                              'rgb(240 249 255)',
                  color:      p.party_role === 'university' ? 'rgb(67 56 202)' :
                              p.party_role === 'student'    ? 'rgb(180 83 9)' :
                                                              'rgb(7 89 133)',
                }">
            <Building2 v-if="p.party_role === 'university'" class="w-4 h-4" />
            <User v-else class="w-4 h-4" />
          </span>
          <div class="flex-1 min-w-0">
            <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">
              {{ PARTY_LABELS[p.party_role] || p.party_role }}
            </div>
            <div class="font-bold text-slate-900 dark:text-slate-100">{{ p.full_name }}</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              <span v-if="p.passport_series" class="font-mono">{{ p.passport_series }}</span>
              <span v-if="p.pinfl"> · PINFL {{ p.pinfl }}</span>
              <span v-if="p.phone"> · {{ p.phone }}</span>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <!-- Contract metadata -->
    <section class="card p-6 sm:p-7">
      <h2 class="font-bold text-lg mb-4 text-slate-900 dark:text-slate-100">Shartnoma haqida</h2>
      <dl class="grid sm:grid-cols-2 gap-x-8 gap-y-4">
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Yaratilgan</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100">{{ fmtDate(contract.created_at) }}</dd>
        </div>
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Imzolangan</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100">
            {{ contract.signed_at ? fmtDate(contract.signed_at) : 'Hali yo\'q' }}
          </dd>
        </div>
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Turi</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100">{{ tr(CONTRACT_TYPE, contract.type) }}</dd>
        </div>
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Valyuta</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100">{{ contract.currency }}</dd>
        </div>
      </dl>
    </section>
  </div>
</template>
