<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import {
  ArrowLeft, CreditCard, FileText, CheckCircle2, XCircle, RotateCcw,
  Plus, Receipt, Wallet, AlertTriangle, Paperclip, Calendar, ArrowDown,
} from 'lucide-vue-next'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import { paymentsApi, type PaymentRead, type PaymentStatus } from '@/api/payments.api'
import { dictionariesApi, type DictionaryItem } from '@/api/dictionaries.api'
import { staffApi } from '@/api/staff.api'
import type { ApplicationDetailed } from '@/api/applications.api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import FileUpload from '@/components/ui/FileUpload.vue'
import { fileUrl } from '@/utils/files'
import { PAYMENT_STATUS, CONTRACT_STATUS, tr } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { ask } = useConfirm()

const contractId = computed(() => route.params.contractId as string)

const contract = ref<ContractDetailed | null>(null)
const application = ref<ApplicationDetailed | null>(null)
const payments = ref<PaymentRead[]>([])
const methods = ref<DictionaryItem[]>([])
const loading = ref(true)
const openingPdf = ref(false)

const hasPdf = computed(() => !!contract.value?.pdf_file_id && !!contract.value?.signed_at)

// The student party row carries the applicant's name on the contract
// itself — fall back to it when the application fetch hasn't resolved.
const applicantName = computed(() => {
  if (application.value) {
    const a: any = application.value
    if (a.applicant_full_name) return a.applicant_full_name as string
  }
  const student = contract.value?.parties?.find(p => p.party_role === 'student')
  return student?.full_name || null
})

const newPayment = reactive({
  amount: '' as string,
  payment_method_id: '' as string,
  reference: '' as string,
  notes: '' as string,
  paid_at: '' as string,
  receipt_file_id: null as string | null,
})
const formError = ref<string | null>(null)
const submitting = ref(false)

async function loadAll() {
  loading.value = true
  try {
    const [c, ps, ms] = await Promise.all([
      contractsApi.get(contractId.value),
      paymentsApi.forContract(contractId.value),
      dictionariesApi.items('payment_methods').catch(() => []),
    ])
    contract.value = c
    payments.value = ps
    methods.value = ms
    // Pull the application separately so we can surface
    // applicant_full_name / program_name / branch_name in the header.
    // Don't block the whole page on it — fail silently if forbidden.
    staffApi.applications.get(c.application_id)
      .then(a => { application.value = a })
      .catch(() => { /* ignore — header just falls back to the contract.parties student name */ })
    // Pre-fill amount with the remaining balance for convenience
    const balance = Number(c.total_amount) - Number(c.paid_amount)
    newPayment.amount = balance > 0 ? String(balance) : ''
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

async function openContractPdf() {
  if (!contract.value || !hasPdf.value) return
  openingPdf.value = true
  try {
    await contractsApi.openPdf(contract.value.id)
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "PDF ochib bo'lmadi")
  } finally {
    openingPdf.value = false
  }
}

onMounted(loadAll)

// === Derived ===
const balance = computed(() => {
  if (!contract.value) return 0
  return Number(contract.value.total_amount) - Number(contract.value.paid_amount)
})
const progressPercent = computed(() => {
  if (!contract.value) return 0
  const total = Number(contract.value.total_amount) || 0
  if (total <= 0) return 0
  return Math.min(100, Math.round((Number(contract.value.paid_amount) / total) * 100))
})
const paymentTone = computed<'paid' | 'partial' | 'unpaid'>(() => {
  if (!contract.value) return 'unpaid'
  const total = Number(contract.value.total_amount) || 0
  const paid = Number(contract.value.paid_amount) || 0
  if (paid >= total && total > 0) return 'paid'
  if (paid > 0) return 'partial'
  return 'unpaid'
})

// === Actions ===
async function submitPayment() {
  formError.value = null
  if (!contract.value) return
  const amount = Number(newPayment.amount)
  if (!amount || amount <= 0) {
    formError.value = "Summa noto'g'ri yoki bo'sh"
    return
  }
  if (!newPayment.payment_method_id) {
    formError.value = "To'lov turini tanlang"
    return
  }
  submitting.value = true
  try {
    await paymentsApi.create({
      contract_id: contract.value.id,
      amount: newPayment.amount,
      payment_method_id: newPayment.payment_method_id,
      reference: newPayment.reference.trim() || null,
      notes: newPayment.notes.trim() || null,
      receipt_file_id: newPayment.receipt_file_id,
      // Send paid_at only when the accountant picked a date — empty
      // string falls back to "now" on the server. Submitting "" would
      // hit Pydantic's date validator and 422.
      paid_at: newPayment.paid_at || undefined,
    })
    toast.success("To'lov yaratildi (kutilayotgan holatda). Tasdiqlash kerak.")
    Object.assign(newPayment, {
      amount: '', payment_method_id: '', reference: '', notes: '',
      paid_at: '', receipt_file_id: null,
    })
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string; error?: { message?: string } }>
    formError.value = ax.response?.data?.detail
      || ax.response?.data?.error?.message
      || "Saqlab bo'lmadi"
  } finally {
    submitting.value = false
  }
}

function fillBalance() {
  newPayment.amount = balance.value > 0 ? String(balance.value) : '0'
}

/**
 * Two-way mask for the summa input. The raw numeric value lives in
 * newPayment.amount as a digit-only string ("1000000"); the input shows
 * the prettified form ("1 000 000"). Stripping on `set` is what keeps
 * paste-from-Excel ("1,000,000.00") and accidental space-typing both
 * harmless — we always normalise back to digits before storing.
 */
const amountDisplay = computed<string>({
  get() {
    if (!newPayment.amount) return ''
    const [intPart, decPart] = String(newPayment.amount).split('.')
    const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
    return decPart !== undefined ? `${grouped}.${decPart}` : grouped
  },
  set(v: string) {
    // Keep digits + a single dot; first dot survives, rest are dropped.
    let cleaned = v.replace(/[^\d.]/g, '')
    const dot = cleaned.indexOf('.')
    if (dot !== -1) {
      cleaned = cleaned.slice(0, dot + 1) + cleaned.slice(dot + 1).replace(/\./g, '')
    }
    newPayment.amount = cleaned
  },
})

/**
 * Default the "to'lov sanasi" date input to today (YYYY-MM-DD) — that's
 * the most common case, but the accountant can pick a back-date when
 * entering a payment that physically cleared a few days earlier.
 */
const todayIso = computed(() => new Date().toISOString().slice(0, 10))

async function confirmPayment(p: PaymentRead) {
  const ok = await ask({
    title: "To'lovni tasdiqlash",
    message: `${fmtMoney(p.amount)} ${p.currency} miqdoridagi to'lov tasdiqlansinmi?`,
    confirmLabel: "Tasdiqlash",
    tone: 'primary',
  })
  if (!ok) return
  try {
    await paymentsApi.confirm(p.id)
    toast.success("Tasdiqlandi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

async function failPayment(p: PaymentRead) {
  const reason = window.prompt("Sabab (ixtiyoriy):") || ''
  const ok = await ask({
    title: "Bajarilmagan deb belgilash",
    message: `${fmtMoney(p.amount)} ${p.currency} bajarilmagan deb belgilansinmi?`,
    confirmLabel: "Tasdiqlash",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await paymentsApi.fail(p.id, reason || undefined)
    toast.success("Belgilandi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

async function refundPayment(p: PaymentRead) {
  const reason = window.prompt("Qaytarish sababi:") || ''
  const ok = await ask({
    title: "Qaytarish",
    message: `${fmtMoney(p.amount)} ${p.currency} qaytarilsinmi?`,
    confirmLabel: "Qaytarish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await paymentsApi.refund(p.id, reason || undefined)
    toast.success("Qaytarildi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
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
function methodName(id: string): string {
  return methods.value.find(m => m.id === id)?.name_uz || '—'
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
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="contract" class="space-y-5">
    <PageHeader
      :title="`Shartnoma ${contract.contract_number}`"
      :subtitle="`Turi: ${contract.type === 'three_party' ? 'Uch tomonlama' : 'Ikki tomonlama'} · ${tr(CONTRACT_STATUS, contract.status)}`"
      :crumbs="[
        { label: 'Bosh sahifa', to: '/accountant' },
        { label: 'Shartnomalar', to: '/accountant/contracts' },
        { label: contract.contract_number },
      ]"
    >
      <button v-if="hasPdf" class="btn-outline" :disabled="openingPdf" @click="openContractPdf">
        <FileText class="w-4 h-4" />
        {{ openingPdf ? 'Ochilmoqda...' : 'PDF ni ochish' }}
      </button>
      <button class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <!-- Applicant identity card — accountant needs to see WHO this
         contract belongs to without a detour to the contract detail
         page. F.I.Sh. + Yo'nalish + Filial + PDF in one place. -->
    <section class="card p-4 sm:p-5">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3 min-w-0 flex-1">
          <div class="grid place-items-center w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white text-base font-bold shrink-0 shadow-sm">
            {{ (applicantName || '?').split(/\s+/).slice(0, 2).map(s => s[0]).join('').toUpperCase() }}
          </div>
          <div class="min-w-0">
            <div class="text-lg font-bold text-slate-900 dark:text-slate-100 truncate">
              {{ applicantName || '—' }}
            </div>
            <div class="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span v-if="application?.program_name" class="inline-flex items-center gap-1">
                <span class="font-medium text-slate-700 dark:text-slate-300">{{ application.program_name }}</span>
              </span>
              <span v-if="application?.branch_name">· {{ application.branch_name }}</span>
              <span v-if="application?.education_level_name">· {{ application.education_level_name }}</span>
              <span v-if="application?.education_form_name">· {{ application.education_form_name }}</span>
            </div>
            <div v-if="application?.application_number" class="mt-1 text-[11px] font-mono text-slate-400 dark:text-slate-500">
              Ariza №: {{ application.application_number }}
            </div>
          </div>
        </div>

        <!-- Side-rail: PDF + status quick states -->
        <div v-if="hasPdf || !contract.signed_at" class="shrink-0">
          <button v-if="hasPdf" type="button"
                  class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300 dark:hover:bg-rose-500/25 transition"
                  :disabled="openingPdf"
                  @click="openContractPdf">
            <FileText class="w-4 h-4" />
            {{ openingPdf ? 'Ochilmoqda...' : 'Shartnoma PDF' }}
          </button>
          <div v-else class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300">
            <AlertTriangle class="w-3.5 h-3.5" />
            PDF imzodan keyin yuklanadi
          </div>
        </div>
      </div>
    </section>

    <!-- Contract balance summary -->
    <section class="card p-4 sm:p-6">
      <div class="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
            <span class="grid place-items-center w-8 h-8 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <Wallet class="w-4 h-4" />
            </span>
            To'lov holati
          </h2>
        </div>
        <StatusBadge :status="contract.status" :label="tr(CONTRACT_STATUS, contract.status)" />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div class="rounded-xl p-3 ring-1 ring-slate-200/70 dark:ring-slate-700/40 bg-slate-50/50 dark:bg-slate-800/30">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Jami summa</div>
          <div class="mt-1 text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ fmtMoney(contract.total_amount) }} <span class="text-sm font-normal text-slate-500">{{ contract.currency }}</span></div>
        </div>
        <div class="rounded-xl p-3 ring-1 ring-emerald-200/70 dark:ring-emerald-700/40 bg-emerald-50/50 dark:bg-emerald-500/10">
          <div class="text-[10px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300 font-semibold">To'langan</div>
          <div class="mt-1 text-xl font-bold tabular-nums text-emerald-700 dark:text-emerald-300">{{ fmtMoney(contract.paid_amount) }} <span class="text-sm font-normal opacity-70">{{ contract.currency }}</span></div>
        </div>
        <div class="rounded-xl p-3 ring-1"
             :class="paymentTone === 'paid'
               ? 'ring-emerald-200/70 dark:ring-emerald-700/40 bg-emerald-50/50 dark:bg-emerald-500/10'
               : 'ring-rose-200/70 dark:ring-rose-700/40 bg-rose-50/50 dark:bg-rose-500/10'">
          <div class="text-[10px] uppercase tracking-wider font-semibold"
               :class="paymentTone === 'paid' ? 'text-emerald-700 dark:text-emerald-300' : 'text-rose-700 dark:text-rose-300'">
            Qoldiq
          </div>
          <div class="mt-1 text-xl font-bold tabular-nums"
               :class="paymentTone === 'paid' ? 'text-emerald-700 dark:text-emerald-300' : 'text-rose-700 dark:text-rose-300'">
            {{ fmtMoney(balance) }} <span class="text-sm font-normal opacity-70">{{ contract.currency }}</span>
          </div>
        </div>
      </div>

      <!-- Progress bar -->
      <div class="flex items-center gap-3">
        <div class="flex-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div class="h-full transition-all"
               :class="paymentTone === 'paid' ? 'bg-emerald-500'
                     : paymentTone === 'partial' ? 'bg-amber-500'
                     : 'bg-rose-500'"
               :style="{ width: progressPercent + '%' }"></div>
        </div>
        <span class="text-sm font-bold tabular-nums shrink-0"
              :class="paymentTone === 'paid' ? 'text-emerald-600 dark:text-emerald-400'
                    : paymentTone === 'partial' ? 'text-amber-600 dark:text-amber-400'
                    : 'text-rose-600 dark:text-rose-400'">
          {{ progressPercent }}%
        </span>
      </div>
    </section>

    <!-- New payment form -->
    <section v-if="contract.status !== 'cancelled'" class="card p-4 sm:p-6">
      <div class="flex items-center gap-2 mb-4">
        <span class="grid place-items-center w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300">
          <Plus class="w-4 h-4" />
        </span>
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Yangi to'lov qo'shish</h2>
      </div>

      <div v-if="formError" class="mb-3 text-sm rounded-lg p-3 bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 inline-flex items-center gap-2">
        <AlertTriangle class="w-4 h-4 shrink-0" /> {{ formError }}
      </div>

      <div class="grid sm:grid-cols-2 gap-4">
        <!-- Summa — biggest, mono, thousands-separated, currency suffix -->
        <div class="sm:col-span-2">
          <label class="field-label">Summa <span class="text-rose-500">*</span></label>
          <div class="relative">
            <input v-model="amountDisplay" inputmode="decimal" autocomplete="off"
                   class="input pr-32 pl-4 font-mono text-2xl tabular-nums tracking-wider h-14"
                   placeholder="0" />
            <span class="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-400 dark:text-slate-500 pointer-events-none">
              {{ contract.currency }}
            </span>
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
            <span class="text-slate-500 dark:text-slate-400">Joriy qoldiq:</span>
            <strong class="font-mono tabular-nums text-slate-900 dark:text-slate-100">
              {{ fmtMoney(balance) }} {{ contract.currency }}
            </strong>
            <button v-if="balance > 0" type="button"
                    class="ml-auto inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-md bg-brand-50 text-brand-700 ring-1 ring-brand-200 dark:bg-brand-500/15 dark:text-brand-300 dark:ring-brand-400/30 hover:bg-brand-100 dark:hover:bg-brand-500/25 transition"
                    @click="fillBalance">
              <ArrowDown class="w-3 h-3" /> Qoldiqni qo'yish
            </button>
          </div>
        </div>

        <!-- To'lov turi -->
        <div>
          <label class="field-label">To'lov turi <span class="text-rose-500">*</span></label>
          <select v-model="newPayment.payment_method_id" class="input">
            <option value="">— tanlang —</option>
            <option v-for="m in methods" :key="m.id" :value="m.id">{{ m.name_uz }}</option>
          </select>
        </div>

        <!-- To'lov sanasi — defaults to today via placeholder, optional -->
        <div>
          <label class="field-label inline-flex items-center gap-1.5">
            <Calendar class="w-3 h-3" /> To'lov sanasi
          </label>
          <input v-model="newPayment.paid_at" type="date" class="input"
                 :max="todayIso" :placeholder="todayIso" />
          <p class="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            Bo'sh qoldirilsa — bugungi sana ishlatiladi.
          </p>
        </div>

        <!-- Tranzaksiya raqami -->
        <div>
          <label class="field-label">Tranzaksiya / chek raqami</label>
          <input v-model="newPayment.reference" class="input font-mono"
                 placeholder="TR-2026-001234" autocomplete="off" />
          <p class="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            Bank chiqindisi yoki to'lov tizimi raqami (ixtiyoriy).
          </p>
        </div>

        <!-- Izoh — textarea, multi-line -->
        <div>
          <label class="field-label">Izoh</label>
          <textarea v-model="newPayment.notes" rows="2"
                    class="input resize-none"
                    placeholder="Masalan: Qisman to'lov, qolgani 25-iyungacha"></textarea>
        </div>

        <!-- Chek (file upload) -->
        <div class="sm:col-span-2">
          <label class="field-label inline-flex items-center gap-1">
            <Paperclip class="w-3 h-3" /> Chek (rasm yoki PDF, ixtiyoriy)
          </label>
          <FileUpload :model-value="newPayment.receipt_file_id"
                      @update:model-value="(v: string | null) => newPayment.receipt_file_id = v"
                      subdir="payment-receipts"
                      hint="To'lov chekining nusxasini yuklang." />
        </div>
      </div>

      <div class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-2">
        <button class="btn-primary" :disabled="submitting" @click="submitPayment">
          <Plus class="w-4 h-4" /> {{ submitting ? 'Saqlanmoqda...' : "To'lov qo'shish" }}
        </button>
      </div>
    </section>

    <!-- Payments list -->
    <section class="card overflow-hidden">
      <div class="p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-violet-50 text-violet-600 dark:bg-violet-500/15 dark:text-violet-300">
            <Receipt class="w-4 h-4" />
          </span>
          <div>
            <h2 class="font-semibold text-slate-900 dark:text-slate-100">To'lov tarixi</h2>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ payments.length }} ta yozuv</p>
          </div>
        </div>
      </div>

      <div v-if="!payments.length" class="p-12">
        <EmptyState :icon="CreditCard" title="Hali to'lovlar yo'q" subtitle="Yuqoridagi formani to'ldiring" />
      </div>

      <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800/60">
        <li v-for="p in payments" :key="p.id" class="p-3 sm:p-5 flex flex-wrap items-start gap-3 sm:gap-4">
          <span class="grid place-items-center w-10 h-10 rounded-xl shrink-0 ring-1"
                :class="statusTone(p.status)">
            <CheckCircle2 v-if="p.status === 'confirmed'" class="w-4 h-4" />
            <Calendar v-else-if="p.status === 'pending'" class="w-4 h-4" />
            <RotateCcw v-else-if="p.status === 'refunded'" class="w-4 h-4" />
            <XCircle v-else class="w-4 h-4" />
          </span>
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span class="font-semibold text-slate-900 dark:text-slate-100 text-base tabular-nums">
                {{ fmtMoney(p.amount) }} <span class="text-xs font-normal text-slate-500">{{ p.currency }}</span>
              </span>
              <span class="font-mono text-[11px] text-slate-400 dark:text-slate-500">{{ p.payment_number }}</span>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1"
                    :class="statusTone(p.status)">
                {{ tr(PAYMENT_STATUS, p.status) }}
              </span>
            </div>
            <div class="mt-1 text-xs text-slate-600 dark:text-slate-400 flex flex-wrap items-center gap-x-3 gap-y-0.5">
              <span class="inline-flex items-center gap-1">
                <CreditCard class="w-3 h-3" /> {{ methodName(p.payment_method_id) }}
              </span>
              <span v-if="p.reference" class="font-mono">№ {{ p.reference }}</span>
              <span class="text-slate-400 dark:text-slate-500">·</span>
              <span class="inline-flex items-center gap-1">
                <Calendar class="w-3 h-3" /> {{ p.paid_at ? fmtDate(p.paid_at) : `Yaratilgan: ${fmtDate(p.created_at)}` }}
              </span>
            </div>
            <p v-if="p.notes" class="mt-2 text-xs text-slate-500 dark:text-slate-400 italic">{{ p.notes }}</p>
            <a v-if="p.receipt_file_id" :href="fileUrl(p.receipt_file_id) || '#'" target="_blank" rel="noopener"
               class="mt-2 inline-flex items-center gap-1.5 text-[11px] font-medium text-brand-600 dark:text-brand-300 hover:underline">
              <FileText class="w-3 h-3" /> Chekni ochish
            </a>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button v-if="p.status === 'pending'" class="btn-outline btn-sm text-emerald-600" @click="confirmPayment(p)">
              <CheckCircle2 class="w-3.5 h-3.5" /> Tasdiqlash
            </button>
            <button v-if="p.status === 'pending'" class="btn-outline btn-sm text-rose-600" @click="failPayment(p)">
              <XCircle class="w-3.5 h-3.5" /> Rad
            </button>
            <button v-if="p.status === 'confirmed'" class="btn-outline btn-sm text-amber-600" @click="refundPayment(p)">
              <RotateCcw class="w-3.5 h-3.5" /> Qaytarish
            </button>
          </div>
        </li>
      </ul>
    </section>
  </div>

  <div v-else class="card p-12 text-center text-slate-500">
    Shartnoma topilmadi.
    <RouterLink to="/accountant/contracts" class="block mt-3 text-brand-600 hover:underline">Shartnomalarga qaytish</RouterLink>
  </div>
</template>
