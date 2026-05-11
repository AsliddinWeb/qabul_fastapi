<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import {
  ArrowLeft, Pencil, Trash2, CheckCircle2, XCircle, PlayCircle,
  User as UserIcon, Award, GraduationCap, FileText,
  FileSignature, Ban, Download, Plus, CreditCard, RotateCcw,
  Clock, Send, Eye, Phone, MapPin, IdCard,
  Building2, Layers, BookOpen, Calendar, Globe, Hash, Wallet,
  AlertTriangle, Inbox, Paperclip, ExternalLink,
  Shield, Users,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi } from '@/api/admin.api'
import { http } from '@/api/http'
import { consultingApi, type ConsultingAgency } from '@/api/consulting.api'
import { useAuthStore } from '@/stores/auth'
import { fileUrl } from '@/utils/files'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { APPLICATION_STATUS, ADMISSION_TYPE, CONTRACT_STATUS, CONTRACT_TYPE, PAYMENT_STATUS, tr } from '@/utils/labels'
import FileUpload from '@/components/ui/FileUpload.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import LoginInfoCard from '@/components/ui/LoginInfoCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const { ask } = useConfirm()
const canSeeConsulting = computed(() => auth.isConsulting)

const id = computed(() => route.params.id as string)
const panelPrefix = computed(() => {
  if (route.path.startsWith('/operator/')) return '/operator'
  if (route.path.startsWith('/accountant/')) return '/accountant'
  return '/admin'
})
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')
const isAccountantPanel = computed(() => panelPrefix.value === '/accountant')

const loading = ref(true)
const application = ref<any>(null)
const applicant = ref<any>(null)
const program = ref<any>(null)
const branch = ref<any>(null)
const educationLevel = ref<any>(null)
const educationForm = ref<any>(null)
const diplom = ref<any>(null)
const transferDiplom = ref<any>(null)
const contract = ref<any>(null)
const cancelledContracts = ref<any[]>([])
const contractTemplates = ref<any[]>([])
const payments = ref<any[]>([])
const lead = ref<any>(null)
const consultingAgencies = ref<ConsultingAgency[]>([])
const consultingSelected = ref<string>('')
const savingConsulting = ref(false)
// Referral row attached to this applicant (if anyone invited them).
const referralRow = ref<any>(null)
// Map of user_id → { full_name, phone, role } for the actor card.
const actorMap = ref<Record<string, { full_name: string | null; phone: string | null; role: string | null; referral_code: string | null }>>({})

function authHeader(): Record<string, string> {
  const t = localStorage.getItem('access_token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function loadAll() {
  loading.value = true
  try {
    application.value = await adminApi.applications.get(id.value)

    const [ap, p, br, lvl, formsList] = await Promise.all([
      adminApi.applicants.get(application.value.applicant_id).catch(() => null),
      adminApi.programs.get(application.value.program_id).catch(() => null),
      adminApi.branches.list(false).catch(() => []),
      adminApi.educationLevels.list().catch(() => []),
      adminApi.educationForms.list().catch(() => []),
    ])
    applicant.value = ap
    program.value = p
    branch.value = (br as any[]).find((x: any) => x.id === application.value.branch_id) || null
    educationLevel.value = (lvl as any[]).find((x: any) => x.id === application.value.education_level_id) || null
    educationForm.value = (formsList as any[]).find((x: any) => x.id === application.value.education_form_id) || null

    if (ap?.user_id) {
      const [dList, tList, eduTypes, instTypes, courses, regions, countries] = await Promise.all([
        adminApi.diploms.list({ user_id: ap.user_id }).catch(() => ({ items: [] }) as any),
        adminApi.transferDiploms.list({ user_id: ap.user_id }).catch(() => ({ items: [] }) as any),
        adminApi.educationTypes.list().catch(() => []),
        adminApi.institutionTypes.list().catch(() => []),
        adminApi.courses.list().catch(() => []),
        // We don't know which country, so fetch countries flat-list:
        adminApi.regions.list().catch(() => []),
        adminApi.countries.list().catch(() => []),
      ])
      diplom.value = (dList as any).items?.[0] || null
      transferDiplom.value = (tList as any).items?.[0] || null

      // Resolve nested labels for the cards
      const lookup = (arr: any[], id: string) => arr.find((x: any) => x.id === id)?.name || null
      if (diplom.value) {
        diplom.value._education_type = lookup(eduTypes as any[], diplom.value.education_type_id)
        diplom.value._institution_type = lookup(instTypes as any[], diplom.value.institution_type_id)
        diplom.value._region = lookup(regions as any[], diplom.value.region_id)
        // district loaded on demand
        if (diplom.value.region_id) {
          const districts = await adminApi.districts.list(diplom.value.region_id).catch(() => [])
          diplom.value._district = lookup(districts as any[], diplom.value.district_id)
        }
      }
      if (transferDiplom.value) {
        transferDiplom.value._country = lookup(countries as any[], transferDiplom.value.country_id)
        transferDiplom.value._course = lookup(courses as any[], transferDiplom.value.target_course_id)
      }
    }

    // Load contract templates (active ones)
    const tmplRes = await fetch('/api/v1/contracts/templates', { headers: authHeader() })
    contractTemplates.value = await tmplRes.json().catch(() => [])

    // Load contracts for this application — split into active vs cancelled history
    const contractsRes = await adminApi.contracts.list({ size: 100 }).catch(() => ({ items: [] } as any))
    const allForApp = (contractsRes.items as any[]).filter((c: any) => c.application_id === id.value)
    contract.value = allForApp.find((c: any) => c.status !== 'cancelled') || null
    cancelledContracts.value = allForApp
      .filter((c: any) => c.status === 'cancelled')
      .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    // Payments for this contract
    if (contract.value) {
      payments.value = await adminApi.payments.listForContract(contract.value.id).catch(() => [])
    } else {
      payments.value = []
    }

    // If this application was converted from a Lead, load it for the widget
    if (application.value.lead_id) {
      try {
        const { leadsApi } = await import('@/api/leads.api')
        lead.value = await leadsApi.get(application.value.lead_id)
      } catch { lead.value = null }
    } else {
      lead.value = null
    }

    // Consulting agencies (only fetched for users with is_consulting=true)
    if (canSeeConsulting.value) {
      consultingAgencies.value = await consultingApi.list(true).catch(() => [])
      consultingSelected.value = application.value.consulting_agency_id || ''
    }

    // Referral row attached to this applicant (if any). Best-effort —
    // ignore 403s for users without applicants.list (e.g. accountants
    // viewing through their read-only path).
    if (applicant.value) {
      try {
        const { referralsApi } = await import('@/api/referrals.api')
        const refs = await referralsApi.list({ referred_applicant_id: applicant.value.id })
        referralRow.value = refs[0] || null
      } catch { /* ignore */ }
    }

    // Resolve actor names + applicant's own referral_code (so the card can
    // show "Bu abituriyentning kodi") in one batch.
    const ids = new Set<string>()
    if (applicant.value?.user_id) ids.add(applicant.value.user_id)
    if (applicant.value?.registered_by_id) ids.add(applicant.value.registered_by_id)
    if (application.value.reviewed_by_id) ids.add(application.value.reviewed_by_id)
    if (contract.value?.created_by_id) ids.add(contract.value.created_by_id)
    if (referralRow.value?.referrer_user_id) ids.add(referralRow.value.referrer_user_id)
    if (lead.value?.assigned_to_id) ids.add(lead.value.assigned_to_id)
    if (lead.value?.created_by_id) ids.add(lead.value.created_by_id)
    if (ids.size > 0) {
      try {
        const res = await http.get<Array<{
          id: string; full_name: string | null; phone: string | null;
          role: string | null; referral_code: string | null
        }>>('/users/public-lookup', { params: { ids: Array.from(ids).join(',') } })
        const map: Record<string, any> = {}
        for (const u of res.data) {
          map[u.id] = {
            full_name: u.full_name,
            phone: u.phone,
            role: u.role,
            referral_code: u.referral_code,
          }
        }
        actorMap.value = map
      } catch { /* ignore */ }
    }
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadAll(), loadPaymentMethods()])
})

// =============================================================================
// Status timeline (4 steps based on status)
// =============================================================================
const TIMELINE_STEPS = [
  { key: 'topshirildi',       label: 'Topshirildi',       icon: Send },
  { key: 'korib_chiqilmoqda', label: "Ko'rib chiqilmoqda", icon: Eye },
  { key: 'qabul_qilindi',     label: 'Qabul qilindi',     icon: CheckCircle2 },
] as const

const stepIndex = computed(() => {
  if (!application.value) return -1
  const s = application.value.status
  if (s === 'rad_etildi') return -2  // special: rejected
  return TIMELINE_STEPS.findIndex((step) => step.key === s)
})

// Status palette — 2-stop, calmer
const STATUS_BANNER: Record<string, string> = {
  topshirildi:        'from-amber-500 to-orange-600',
  korib_chiqilmoqda:  'from-indigo-600 to-violet-700',
  qabul_qilindi:      'from-emerald-600 to-teal-700',
  rad_etildi:         'from-rose-600 to-red-700',
}
const STATUS_ACCENT_TEXT: Record<string, string> = {
  topshirildi: 'text-amber-700',
  korib_chiqilmoqda: 'text-indigo-700',
  qabul_qilindi: 'text-emerald-700',
  rad_etildi: 'text-rose-700',
}

// =============================================================================
// Actions
// =============================================================================
async function saveConsulting() {
  savingConsulting.value = true
  try {
    await adminApi.applications.update(id.value, {
      consulting_agency_id: consultingSelected.value || null,
    })
    toast.success(consultingSelected.value
      ? "Konsalting agentligi biriktirildi"
      : "Konsalting agentligi olib tashlandi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    savingConsulting.value = false
  }
}

async function startReview() {
  try {
    await adminApi.applications.startReview(id.value)
    toast.success("Ko'rib chiqishga olindi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function approve() {
  const ok = await ask({
    title: "Arizani qabul qilish",
    message: `${application.value.application_number} arizasi qabul qilinsinmi? Shartnoma yaratish imkoniyati ochiladi.`,
    confirmLabel: "Qabul qilish",
    tone: 'primary',
  })
  if (!ok) return
  try {
    await adminApi.applications.review(id.value, { approved: true })
    toast.success("Qabul qilindi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function reject() {
  const reason = window.prompt("Rad etish sababi (ixtiyoriy):") || ''
  const ok = await ask({
    title: "Arizani rad etish",
    message: `${application.value.application_number} arizasi rad etilsinmi?`,
    confirmLabel: "Rad etish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.applications.review(id.value, { approved: false, rejection_reason: reason || undefined })
    toast.success("Rad etildi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function removeApp() {
  const ok = await ask({
    title: "Arizani o'chirish",
    message: `${application.value.application_number} arizasi o'chirilsinmi? Bu amalni qaytarib bo'lmaydi.`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.applications.delete(id.value)
    toast.success("O'chirildi")
    router.push(`${panelPrefix.value}/applications`)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi")
  }
}

// =============================================================================
// Contract create
// =============================================================================
const showContractForm = ref(false)
const contractForm = reactive({
  template_id: '',
  type: 'two_party' as 'two_party' | 'three_party',
  total_amount: null as number | null,
  currency: 'UZS',
})
const contractCreating = ref(false)

const compatibleTemplates = computed(() =>
  contractTemplates.value.filter((t: any) => {
    if (!t.is_active) return false
    return contractForm.type === 'three_party' ? !!t.body_three_party : !!t.body_two_party
  })
)

// Display value with thousand separators ("9 520 000"), kept in sync with
// contractForm.total_amount (number). Also used by the input @input handler.
const contractAmountDisplay = ref('')
function fmtSeparated(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(Number(n))) return ''
  return Number(Math.floor(n)).toLocaleString('uz-UZ').replace(/,/g, ' ')
}
function onContractAmountInput(e: Event) {
  // Only digits — drop everything else, including dots (don't let .00 inflate).
  const raw = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const n = raw ? parseInt(raw, 10) : null
  contractForm.total_amount = n
  contractAmountDisplay.value = n === null ? '' : fmtSeparated(n)
}

function openContractForm() {
  showContractForm.value = true
  if (program.value?.tuition_fee) {
    const n = Math.floor(Number(program.value.tuition_fee))
    contractForm.total_amount = n
    contractAmountDisplay.value = fmtSeparated(n)
  } else {
    contractAmountDisplay.value = ''
  }
}

async function createContract() {
  if (!contractForm.template_id) {
    toast.error("Shablonni tanlang")
    return
  }
  contractCreating.value = true
  try {
    const payload: any = {
      application_id: id.value,
      template_id: contractForm.template_id,
      type: contractForm.type,
      currency: contractForm.currency,
      total_amount: contractForm.total_amount,
    }
    const res = await fetch('/api/v1/contracts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const j = await res.json().catch(() => null)
      throw new Error(j?.error?.message || `${res.status}`)
    }
    toast.success("Shartnoma yaratildi")
    showContractForm.value = false
    await loadAll()
  } catch (e: any) {
    toast.error(e.message || "Saqlab bo'lmadi")
  } finally {
    contractCreating.value = false
  }
}

async function signContract() {
  const ok = await ask({
    title: "Shartnomani imzolash",
    message: `${contract.value.contract_number} imzolanganligi tasdiqlansinmi?`,
    confirmLabel: "Imzolash",
    tone: 'primary',
  })
  if (!ok) return
  try {
    await adminApi.contracts.sign(contract.value.id)
    toast.success("Imzolandi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function cancelContract() {
  const ok = await ask({
    title: "Shartnomani bekor qilish",
    message: `${contract.value.contract_number} bekor qilinsinmi?`,
    confirmLabel: "Bekor qilish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.contracts.cancel(contract.value.id)
    toast.success("Bekor qilindi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

// =============================================================================
// Payment create
// =============================================================================
const showPaymentForm = ref(false)
const paymentMethods = ref<Array<{ id: string; code: string; name_uz: string }>>([])
const paymentSaving = ref(false)
const paymentForm = reactive({
  amount: null as number | null,
  payment_method_id: '',
  reference: '',
  receipt_file_id: null as string | null,
})

const PAYMENT_METHOD_ICONS: Record<string, string> = {
  cash:   '💵',
  bank:   '🏦',
  click:  '🟦',
  payme:  '🟩',
  uzcard: '💳',
  humo:   '💳',
}

async function loadPaymentMethods() {
  try {
    const items = await adminApi.dictionaries.items('payment_methods')
    paymentMethods.value = items.filter((i: any) => i.is_active !== false)
  } catch { paymentMethods.value = [] }
}

const fmtMoneyLive = computed(() => {
  if (paymentForm.amount == null || isNaN(paymentForm.amount)) return ''
  return Number(paymentForm.amount).toLocaleString('uz-UZ').replace(/,/g, ' ')
})

async function createPayment() {
  if (!paymentForm.amount || paymentForm.amount <= 0) {
    toast.error("To'lov summasini kiriting")
    return
  }
  if (!paymentForm.payment_method_id) {
    toast.error("To'lov turini tanlang")
    return
  }
  paymentSaving.value = true
  try {
    const res = await fetch('/api/v1/payments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify({
        contract_id: contract.value.id,
        amount: paymentForm.amount,
        payment_method_id: paymentForm.payment_method_id,
        reference: paymentForm.reference || null,
        receipt_file_id: paymentForm.receipt_file_id || null,
      }),
    })
    if (!res.ok) {
      const j = await res.json().catch(() => null)
      throw new Error(j?.error?.message || `${res.status}`)
    }
    toast.success("To'lov qo'shildi")
    showPaymentForm.value = false
    paymentForm.amount = null
    paymentForm.payment_method_id = ''
    paymentForm.reference = ''
    paymentForm.receipt_file_id = null
    payments.value = await adminApi.payments.listForContract(contract.value.id).catch(() => [])
  } catch (e: any) {
    toast.error(e.message || "Saqlab bo'lmadi")
  } finally {
    paymentSaving.value = false
  }
}

async function openReceipt(file_id: string) {
  try {
    const { http } = await import('@/api/http')
    const res = await http.get(`/files/${file_id}/download`, { responseType: 'blob' })
    const ct = (res.headers as any)['content-type']
    const blob = new Blob([res.data], { type: typeof ct === 'string' ? ct : 'application/octet-stream' })
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank')
    if (!win) {
      const a = document.createElement('a'); a.href = url; a.target = '_blank'; a.click()
    }
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (e) {
    toast.error("Chekni ochib bo'lmadi")
  }
}

async function confirmPayment(p: any) {
  const reference = window.prompt("Tasdiqlash uchun reference (chek raqami):", p.reference || '') || ''
  if (!reference) return
  try {
    await adminApi.payments.confirm(p.id, { reference })
    toast.success("Tasdiqlandi")
    payments.value = await adminApi.payments.listForContract(contract.value.id).catch(() => [])
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function refundPayment(p: any) {
  const reason = window.prompt("Qaytarish sababi:") || ''
  const ok = await ask({
    title: "To'lovni qaytarish",
    message: `${p.payment_number} qaytarilsinmi?`,
    confirmLabel: "Qaytarish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.payments.refund(p.id, reason)
    toast.success("Qaytarildi")
    payments.value = await adminApi.payments.listForContract(contract.value.id).catch(() => [])
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

// Helpers
function fmtMoney(v: any): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!n || isNaN(n)) return '0'
  return Number(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}
function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short', year: 'numeric' })
}

// Days the lead spent in funnel before being converted (or until now if still open).
const daysInFunnel = computed(() => {
  if (!lead.value) return 0
  const start = new Date(lead.value.created_at).getTime()
  const end = lead.value.converted_at ? new Date(lead.value.converted_at).getTime() : Date.now()
  return Math.max(0, Math.round((end - start) / 86400000))
})

const totalPaid = computed(() => payments.value.filter((p) => p.status === 'confirmed').reduce((s, p) => s + Number(p.amount || 0), 0))
const totalDue = computed(() => Number(contract.value?.total_amount || 0))
const remaining = computed(() => Math.max(0, totalDue.value - totalPaid.value))
const paidPercent = computed(() => totalDue.value ? Math.round((totalPaid.value / totalDue.value) * 100) : 0)

// Avatar — 2-stop, restrained
const AVATAR_COLORS = [
  'from-slate-600 to-slate-800',
  'from-indigo-500 to-indigo-700',
  'from-violet-500 to-violet-700',
  'from-teal-500 to-teal-700',
  'from-amber-500 to-amber-700',
]
function avatarColor(s: string): string {
  const h = s.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}
function applicantInitials(): string {
  if (!applicant.value) return '?'
  const ln = applicant.value.last_name?.[0] || ''
  const fn = applicant.value.first_name?.[0] || ''
  return (ln + fn).toUpperCase() || '?'
}
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="application" class="space-y-6">
    <!-- Back button -->
    <button class="inline-flex items-center gap-1 text-sm text-violet-600 dark:text-violet-300 hover:underline"
            @click="router.push(`${panelPrefix}/applications`)">
      <ArrowLeft class="w-4 h-4" /> Arizalarga qaytish
    </button>

    <!-- HERO — clean two-tone -->
    <div class="card overflow-hidden">
      <!-- Top band with status gradient -->
      <div class="bg-gradient-to-r p-6 text-white"
           :class="STATUS_BANNER[application.status] || 'from-slate-700 to-slate-900'">
        <div class="flex flex-wrap items-start justify-between gap-5">
          <div class="min-w-0 flex items-center gap-4">
            <div class="hidden sm:grid place-items-center w-12 h-12 rounded-xl bg-white/15 ring-1 ring-white/20">
              <FileText class="w-6 h-6" />
            </div>
            <div class="min-w-0">
              <div class="text-[11px] font-semibold uppercase tracking-wider opacity-80">Ariza raqami</div>
              <h1 class="font-mono text-2xl sm:text-3xl font-bold mt-0.5 break-all">{{ application.application_number }}</h1>
              <div class="mt-2 flex flex-wrap items-center gap-1.5">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                             bg-white/20 ring-1 ring-white/20">
                  {{ tr(APPLICATION_STATUS, application.status) }}
                </span>
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                             bg-white/20 ring-1 ring-white/20">
                  {{ tr(ADMISSION_TYPE, application.admission_type) }}
                </span>
                <span v-if="application.submitted_at"
                      class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                             bg-white/10 ring-1 ring-white/15">
                  <Calendar class="w-3 h-3" /> {{ fmtDate(application.submitted_at) }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="!isAccountantPanel" class="flex flex-wrap items-center gap-1.5">
            <button v-if="application.status === 'topshirildi'"
                    class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white/15 hover:bg-white/25 ring-1 ring-white/20 text-white text-sm font-medium transition"
                    @click="startReview">
              <PlayCircle class="w-4 h-4" /> Ko'rib chiqish
            </button>
            <button v-if="application.status === 'topshirildi' || application.status === 'korib_chiqilmoqda'"
                    class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white text-slate-900 text-sm font-semibold shadow-sm hover:shadow transition"
                    @click="approve">
              <CheckCircle2 class="w-4 h-4" /> Qabul qilish
            </button>
            <button v-if="application.status === 'topshirildi' || application.status === 'korib_chiqilmoqda'"
                    class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white/15 hover:bg-white/25 ring-1 ring-white/20 text-white text-sm font-medium transition"
                    @click="reject">
              <XCircle class="w-4 h-4" /> Rad etish
            </button>
            <RouterLink :to="`${panelPrefix}/applications/${id}/edit`"
                        class="inline-grid place-items-center w-9 h-9 rounded-lg bg-white/15 hover:bg-white/25 ring-1 ring-white/20 text-white transition"
                        title="Tahrirlash">
              <Pencil class="w-4 h-4" />
            </RouterLink>
            <button v-if="!isOperatorPanel"
                    class="inline-grid place-items-center w-9 h-9 rounded-lg bg-white/15 hover:bg-white/25 ring-1 ring-white/20 text-white transition"
                    title="O'chirish" @click="removeApp">
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <!-- Timeline strip on white -->
      <div class="px-6 py-5 bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800">
        <!-- Rejected -->
        <div v-if="stepIndex === -2" class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-rose-100 dark:bg-rose-900/40 grid place-items-center text-rose-600 dark:text-rose-300">
            <AlertTriangle class="w-4 h-4" />
          </div>
          <div>
            <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Ariza rad etildi</div>
            <div v-if="application.rejection_reason" class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Sabab: {{ application.rejection_reason }}
            </div>
          </div>
        </div>

        <!-- Progress -->
        <ol v-else class="flex items-center w-full">
          <li v-for="(step, i) in TIMELINE_STEPS" :key="step.key"
              class="flex items-center"
              :class="i < TIMELINE_STEPS.length - 1 ? 'flex-1' : ''">
            <div class="flex flex-col items-center min-w-[88px]">
              <div class="w-9 h-9 rounded-full grid place-items-center transition shrink-0"
                   :class="i <= stepIndex
                     ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                     : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'">
                <component :is="step.icon" class="w-4 h-4" />
              </div>
              <div class="mt-2 text-[11px] font-medium text-center"
                   :class="i <= stepIndex ? 'text-slate-900 dark:text-slate-100' : 'text-slate-400 dark:text-slate-500'">
                {{ step.label }}
              </div>
              <div v-if="i === 0 && application.submitted_at" class="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                {{ fmtDate(application.submitted_at) }}
              </div>
              <div v-if="i === stepIndex && application.reviewed_at" class="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                {{ fmtDate(application.reviewed_at) }}
              </div>
            </div>
            <div v-if="i < TIMELINE_STEPS.length - 1"
                 class="flex-1 h-0.5 mx-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
              <div class="h-full bg-slate-900 dark:bg-white transition-all"
                   :style="{ width: i < stepIndex ? '100%' : '0%' }"></div>
            </div>
          </li>
        </ol>
      </div>
    </div>

    <!-- Two-column body -->
    <div class="grid lg:grid-cols-3 gap-5">
      <!-- LEFT COLUMN — Applicant + Diplom + Program -->
      <div class="lg:col-span-2 space-y-5">
        <!-- Applicant card -->
        <section class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="section-title inline-flex items-center gap-2">
              <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                <UserIcon class="w-4 h-4" />
              </span>
              Abituriyent
            </h2>
            <RouterLink v-if="applicant" :to="`/admin/applicants/${applicant.id}`"
                        class="text-xs text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 font-medium">
              To'liq profil →
            </RouterLink>
          </div>
          <div v-if="applicant" class="flex items-start gap-4">
            <div class="avatar w-16 h-16 text-base bg-gradient-to-br text-white shadow-md"
                 :class="avatarColor(applicant.id)">
              {{ applicantInitials() }}
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {{ applicant.last_name }} {{ applicant.first_name }}
              </div>
              <div class="text-sm text-slate-500 dark:text-slate-400">{{ applicant.other_name || '' }}</div>
              <div class="mt-3 grid sm:grid-cols-2 gap-y-2 gap-x-4 text-xs">
                <div class="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <Calendar class="w-3.5 h-3.5 text-slate-400" />
                  <span>{{ applicant.birth_date }}</span>
                </div>
                <div class="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <IdCard class="w-3.5 h-3.5 text-slate-400" />
                  <span class="font-mono">{{ applicant.passport_series || '—' }}</span>
                </div>
                <div class="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <span class="text-slate-400">PINFL:</span>
                  <span class="font-mono">{{ applicant.pinfl || '—' }}</span>
                </div>
                <div v-if="applicant.additional_phone" class="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <Phone class="w-3.5 h-3.5 text-slate-400" />
                  <span class="font-mono">{{ applicant.additional_phone }}</span>
                </div>
                <div v-if="applicant.telegram_username" class="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <Send class="w-3.5 h-3.5 text-slate-400" />
                  <a :href="`https://t.me/${applicant.telegram_username}`" target="_blank" rel="noopener" class="hover:underline">@{{ applicant.telegram_username }}</a>
                </div>
                <div v-if="applicant.address" class="flex items-center gap-2 text-slate-600 dark:text-slate-400 sm:col-span-2">
                  <MapPin class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span class="truncate">{{ applicant.address }}</span>
                </div>
                <div v-if="applicant.user_id && actorMap[applicant.user_id]?.referral_code"
                     class="flex items-center gap-2 text-slate-600 dark:text-slate-400 sm:col-span-2">
                  <span class="text-base">🎁</span>
                  <span class="text-slate-400">Referal kodi:</span>
                  <span class="font-mono font-semibold text-rose-700 dark:text-rose-300">{{ actorMap[applicant.user_id].referral_code }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Login info card -->
        <LoginInfoCard v-if="applicant?.user_id" :user-id="applicant.user_id" />

        <!-- Diplom card -->
        <section v-if="application.admission_type === 'yangi_qabul'" class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Award class="w-4 h-4" />
            </span>
            Diplom (1-kurs)
          </h2>
          <div v-if="diplom" class="space-y-3">
            <div class="grid sm:grid-cols-2 gap-3 text-sm">
              <div>
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Seriya raqami</div>
                <div class="font-mono font-semibold text-slate-900 dark:text-slate-100">{{ diplom.serial_number }}</div>
              </div>
              <div>
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Bitirgan yili</div>
                <div class="font-medium text-slate-900 dark:text-slate-100">{{ diplom.graduation_year }}</div>
              </div>
              <div class="sm:col-span-2">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Muassasa</div>
                <div class="text-slate-900 dark:text-slate-100">{{ diplom.university_name }}</div>
              </div>
              <div v-if="diplom._education_type">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Hujjat turi</div>
                <div class="text-slate-900 dark:text-slate-100">{{ diplom._education_type }}</div>
              </div>
              <div v-if="diplom._institution_type">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Muassasa turi</div>
                <div class="text-slate-900 dark:text-slate-100">{{ diplom._institution_type }}</div>
              </div>
              <div v-if="diplom._region">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Viloyat</div>
                <div class="text-slate-900 dark:text-slate-100">{{ diplom._region }}</div>
              </div>
              <div v-if="diplom._district">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Tuman</div>
                <div class="text-slate-900 dark:text-slate-100">{{ diplom._district }}</div>
              </div>
            </div>
            <a v-if="diplom.diploma_file_id"
               :href="fileUrl(diplom.diploma_file_id)!"
               target="_blank" rel="noopener"
               class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 hover:border-brand-400 hover:text-brand-600 transition-colors">
              <FileText class="w-4 h-4" />
              Diplom faylini ko'rish
              <ExternalLink class="w-3.5 h-3.5" />
            </a>
            <p v-else class="text-xs text-slate-500 dark:text-slate-400">Fayl yuklanmagan</p>
          </div>
          <div v-else
               class="flex items-center gap-2 text-sm p-3 rounded-xl
                      bg-amber-50 text-amber-800 ring-1 ring-amber-200
                      dark:bg-amber-900/20 dark:text-amber-300 dark:ring-amber-700/30">
            <AlertTriangle class="w-4 h-4 shrink-0" /> Diplom topilmadi
          </div>
        </section>

        <section v-if="application.admission_type === 'perevod'" class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Globe class="w-4 h-4" />
            </span>
            Perevod diplomi
          </h2>
          <div v-if="transferDiplom" class="space-y-3">
            <div class="grid sm:grid-cols-2 gap-3 text-sm">
              <div class="sm:col-span-2">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Muassasa</div>
                <div class="text-slate-900 dark:text-slate-100">{{ transferDiplom.university_name }}</div>
              </div>
              <div v-if="transferDiplom._country">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Davlat</div>
                <div class="text-slate-900 dark:text-slate-100">{{ transferDiplom._country }}</div>
              </div>
              <div v-if="transferDiplom._course">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">Kurs</div>
                <div class="text-slate-900 dark:text-slate-100">{{ transferDiplom._course }}</div>
              </div>
            </div>
            <a v-if="transferDiplom.transcript_file_id"
               :href="fileUrl(transferDiplom.transcript_file_id)!"
               target="_blank" rel="noopener"
               class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 hover:border-brand-400 hover:text-brand-600 transition-colors">
              <FileText class="w-4 h-4" />
              Transkript faylini ko'rish
              <ExternalLink class="w-3.5 h-3.5" />
            </a>
            <p v-else class="text-xs text-slate-500 dark:text-slate-400">Transkript fayli yuklanmagan</p>
          </div>
          <div v-else
               class="flex items-center gap-2 text-sm p-3 rounded-xl
                      bg-amber-50 text-amber-800 ring-1 ring-amber-200
                      dark:bg-amber-900/20 dark:text-amber-300 dark:ring-amber-700/30">
            <AlertTriangle class="w-4 h-4 shrink-0" /> Perevod diplomi topilmadi
          </div>
        </section>

        <!-- Program card -->
        <section class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <GraduationCap class="w-4 h-4" />
            </span>
            Yo'nalish
          </h2>
          <div v-if="program" class="space-y-3">
            <div>
              <div class="flex items-center gap-2">
                <span class="pill font-mono">{{ program.code }}</span>
                <span class="text-base font-semibold text-slate-900 dark:text-slate-100">{{ program.name }}</span>
              </div>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <span v-if="branch" class="pill"><Building2 class="w-3 h-3" /> {{ branch.name }}</span>
                <span v-if="educationLevel" class="pill"><Layers class="w-3 h-3" /> {{ educationLevel.name }}</span>
                <span v-if="educationForm" class="pill"><BookOpen class="w-3 h-3" /> {{ educationForm.name }}</span>
              </div>
            </div>
            <div class="pt-3 border-t border-slate-100 dark:border-slate-800 grid sm:grid-cols-3 gap-3">
              <div class="rounded-xl p-3 bg-slate-50 ring-1 ring-slate-200/60 dark:bg-slate-800/40 dark:ring-slate-700/40">
                <div class="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <Wallet class="w-3 h-3" /> Yillik to'lov
                </div>
                <div class="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                  {{ fmtMoney(program.tuition_fee) }}
                  <span class="text-xs font-medium text-slate-500">so'm</span>
                </div>
              </div>
              <div class="rounded-xl p-3 bg-slate-50 ring-1 ring-slate-200/60 dark:bg-slate-800/40 dark:ring-slate-700/40">
                <div class="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <Calendar class="w-3 h-3" /> Muddati
                </div>
                <div class="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                  {{ program.study_duration_years }}
                  <span class="text-xs font-medium text-slate-500">yil</span>
                </div>
              </div>
              <div class="rounded-xl p-3 bg-slate-50 ring-1 ring-slate-200/60 dark:bg-slate-800/40 dark:ring-slate-700/40">
                <div class="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <Hash class="w-3 h-3" /> Shartnoma seriyasi
                </div>
                <div class="mt-1 font-mono font-semibold text-slate-900 dark:text-slate-100">{{ program.contract_series }}</div>
              </div>
            </div>
          </div>
        </section>

        <section v-if="application.notes" class="card p-5">
          <h2 class="section-title mb-2">Eslatma</h2>
          <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{{ application.notes }}</p>
        </section>
      </div>

      <!-- RIGHT COLUMN — Lead source + Contract + Payments -->
      <div class="space-y-5">
        <!-- Konsulting agentligi (only for is_consulting users) -->
        <section v-if="canSeeConsulting" class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-3">
            <span class="icon-bubble-sm bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
              <Building2 class="w-4 h-4" />
            </span>
            Konsulting agentligi
          </h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
            Ariza qaysi agentlik orqali kelganini biriktiring (ixtiyoriy).
          </p>
          <select v-model="consultingSelected" class="input mb-3">
            <option value="">— Belgilanmagan —</option>
            <option v-for="a in consultingAgencies" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
          <button class="btn-primary w-full justify-center btn-sm"
                  :disabled="savingConsulting || consultingSelected === (application.consulting_agency_id || '')"
                  @click="saveConsulting">
            {{ savingConsulting ? 'Saqlanmoqda...' : 'Saqlash' }}
          </button>
        </section>

        <!-- Lead source (if this application was converted from a Lead) -->
        <section v-if="lead" class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-3">
            <span class="icon-bubble-sm bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <Inbox class="w-4 h-4" />
            </span>
            Lead manbasi
          </h2>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between gap-2">
              <span class="text-slate-500 dark:text-slate-400">Manba</span>
              <span class="text-slate-900 dark:text-slate-100">{{ lead.source_name || '—' }}</span>
            </div>
            <div class="flex justify-between gap-2">
              <span class="text-slate-500 dark:text-slate-400">Varonka</span>
              <span class="text-slate-900 dark:text-slate-100">{{ lead.pipeline_name || '—' }}</span>
            </div>
            <div class="flex justify-between gap-2">
              <span class="text-slate-500 dark:text-slate-400">Lead yaratilgan</span>
              <span class="text-slate-900 dark:text-slate-100">{{ fmtDate(lead.created_at) }}</span>
            </div>
            <div class="flex justify-between gap-2">
              <span class="text-slate-500 dark:text-slate-400">Varonkada</span>
              <span class="text-slate-900 dark:text-slate-100">{{ daysInFunnel }} kun</span>
            </div>
            <div v-if="lead.assigned_to_name" class="flex justify-between gap-2">
              <span class="text-slate-500 dark:text-slate-400">Operator</span>
              <span class="text-slate-900 dark:text-slate-100">{{ lead.assigned_to_name }}</span>
            </div>
          </div>
          <RouterLink :to="`${panelPrefix}/leads/${lead.id}`" class="btn-outline btn-sm w-full mt-3 justify-center">
            Lead'ga o'tish
          </RouterLink>
        </section>

        <!-- Contract card -->
        <section class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <FileText class="w-4 h-4" />
            </span>
            Shartnoma
          </h2>

          <template v-if="!contract">
            <div v-if="application.status !== 'qabul_qilindi'"
                 class="flex items-start gap-2 text-sm p-3 rounded-xl
                        bg-slate-50 text-slate-600 ring-1 ring-slate-200
                        dark:bg-slate-800/40 dark:text-slate-400 dark:ring-slate-700">
              <AlertTriangle class="w-4 h-4 shrink-0 mt-0.5 text-slate-400" />
              <span>Shartnoma yaratish uchun avval ariza qabul qilinishi kerak.</span>
            </div>
            <div v-else-if="!showContractForm">
              <button class="btn-primary w-full" @click="openContractForm">
                <Plus class="w-4 h-4" /> Shartnoma yaratish
              </button>
            </div>
            <div v-else class="space-y-3">
              <div>
                <label class="field-label">Shartnoma turi *</label>
                <div class="flex gap-2">
                  <label class="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm"
                         :class="contractForm.type === 'two_party'
                           ? 'border-brand-600 bg-brand-50 dark:bg-brand-900/30'
                           : 'border-slate-200 dark:border-slate-800'">
                    <input v-model="contractForm.type" type="radio" value="two_party" />
                    <span>2-tomonlama</span>
                  </label>
                  <label class="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm"
                         :class="contractForm.type === 'three_party'
                           ? 'border-brand-600 bg-brand-50 dark:bg-brand-900/30'
                           : 'border-slate-200 dark:border-slate-800'">
                    <input v-model="contractForm.type" type="radio" value="three_party" />
                    <span>3-tomonlama</span>
                  </label>
                </div>
              </div>
              <div>
                <label class="field-label">Shablon *</label>
                <select v-model="contractForm.template_id" class="input">
                  <option value="">— tanlang —</option>
                  <option v-for="t in compatibleTemplates" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
                <p v-if="!compatibleTemplates.length" class="field-hint text-amber-600">
                  Faol shablon yo'q
                </p>
              </div>
              <div>
                <label class="field-label">Jami summa</label>
                <input :value="contractAmountDisplay" @input="onContractAmountInput"
                       type="text" inputmode="numeric" class="input font-mono"
                       placeholder="9 520 000" />
                <p class="field-hint">Yiliga, so'm</p>
              </div>
              <div class="flex gap-2">
                <button class="btn-primary flex-1" :disabled="contractCreating || !compatibleTemplates.length" @click="createContract">
                  {{ contractCreating ? 'Saqlanmoqda...' : 'Yaratish' }}
                </button>
                <button class="btn-ghost" @click="showContractForm = false">Bekor</button>
              </div>
            </div>
          </template>

          <div v-else class="space-y-4">
            <div>
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <div class="font-mono text-xs text-slate-500 dark:text-slate-400">{{ contract.contract_number }}</div>
                  <div class="mt-1 flex flex-wrap items-center gap-1.5">
                    <span class="pill"
                          :class="contract.status === 'signed' ? 'pill-success' :
                                  contract.status === 'cancelled' ? 'pill-danger' : 'pill-warning'">
                      {{ tr(CONTRACT_STATUS, contract.status) }}
                    </span>
                    <span class="pill">{{ tr(CONTRACT_TYPE, contract.type) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="space-y-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <div class="flex justify-between items-baseline">
                <span class="text-xs text-slate-500 dark:text-slate-400">Jami</span>
                <span class="text-base font-bold text-slate-900 dark:text-slate-100">{{ fmtMoney(contract.total_amount) }} {{ contract.currency }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-slate-500 dark:text-slate-400">To'langan</span>
                <span class="text-green-600 dark:text-green-400 font-medium">{{ fmtMoney(totalPaid) }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-slate-500 dark:text-slate-400">Qoldiq</span>
                <span class="text-slate-900 dark:text-slate-100 font-medium">{{ fmtMoney(remaining) }}</span>
              </div>
              <div class="mt-2 h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div class="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all"
                     :style="{ width: paidPercent + '%' }"></div>
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 text-right">{{ paidPercent }}% to'langan</div>
            </div>

            <div class="flex flex-wrap gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button v-if="contract.pdf_file_id" type="button" class="btn-outline btn-sm" @click="adminApi.contracts.openPdf(contract.id)">
                <Download class="w-3.5 h-3.5" /> PDF
              </button>
              <button v-if="contract.status === 'draft'" class="btn-primary btn-sm flex-1" @click="signContract">
                <FileSignature class="w-3.5 h-3.5" /> Imzolash
              </button>
              <button v-if="contract.status !== 'cancelled' && contract.status !== 'completed'"
                      class="btn-outline btn-sm !text-red-600 !border-red-300" @click="cancelContract">
                <Ban class="w-3.5 h-3.5" /> Bekor
              </button>
            </div>
          </div>
        </section>

        <!-- Cancelled contracts history -->
        <section v-if="cancelledContracts.length" class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-3">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Ban class="w-4 h-4" />
            </span>
            Bekor qilingan shartnomalar
            <span class="text-xs text-slate-500 dark:text-slate-400 font-normal">({{ cancelledContracts.length }})</span>
          </h2>
          <ul class="space-y-2">
            <li v-for="cc in cancelledContracts" :key="cc.id"
                class="flex items-center justify-between gap-2 p-3 rounded-xl
                       bg-slate-50 dark:bg-slate-800/40 ring-1 ring-slate-200/60 dark:ring-slate-700/40">
              <div class="min-w-0">
                <div class="font-mono text-xs text-slate-500 dark:text-slate-400">{{ cc.contract_number }}</div>
                <div class="mt-1 flex items-center gap-1.5">
                  <span class="pill">{{ tr(CONTRACT_STATUS, cc.status) }}</span>
                  <span class="text-[11px] text-slate-500 dark:text-slate-400">{{ fmtDate(cc.created_at) }}</span>
                </div>
              </div>
              <button v-if="cc.pdf_file_id" type="button"
                      class="icon-btn" title="PDF ni ochish"
                      @click="adminApi.contracts.openPdf(cc.id)">
                <Download class="w-4 h-4" />
              </button>
            </li>
          </ul>
        </section>

        <!-- Payments card -->
        <section v-if="contract" class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="section-title inline-flex items-center gap-2">
              <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                <CreditCard class="w-4 h-4" />
              </span>
              To'lovlar
              <span v-if="payments.length" class="text-xs text-slate-500 dark:text-slate-400 font-normal">({{ payments.length }})</span>
            </h2>
            <button v-if="!showPaymentForm && contract.status === 'signed'"
                    class="text-xs text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 font-semibold"
                    @click="showPaymentForm = true">
              + Qo'shish
            </button>
          </div>

          <div v-if="showPaymentForm" class="space-y-4 mb-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 ring-1 ring-slate-200/60 dark:ring-slate-700/40">
            <!-- Summa -->
            <div>
              <label class="field-label inline-flex items-center gap-1">
                <Wallet class="w-3.5 h-3.5 text-slate-500" />
                Summa <span class="text-rose-500">*</span>
              </label>
              <div class="relative">
                <input v-model.number="paymentForm.amount"
                       type="number" inputmode="numeric" min="0" step="1000"
                       class="input font-mono text-lg !pr-16 !py-3"
                       placeholder="0" />
                <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-slate-400 pointer-events-none">so'm</span>
              </div>
              <div v-if="fmtMoneyLive" class="mt-1 text-xs text-slate-500 dark:text-slate-400 font-mono">
                {{ fmtMoneyLive }} so'm
              </div>
            </div>

            <!-- Payment method picker -->
            <div>
              <label class="field-label inline-flex items-center gap-1">
                <CreditCard class="w-3.5 h-3.5 text-slate-500" />
                To'lov turi <span class="text-rose-500">*</span>
              </label>
              <div class="grid grid-cols-3 gap-2">
                <button v-for="m in paymentMethods" :key="m.id"
                        type="button"
                        class="px-3 py-2.5 rounded-lg text-xs font-medium ring-1 transition-all flex flex-col items-center gap-1"
                        :class="paymentForm.payment_method_id === m.id
                          ? 'bg-brand-600 text-white ring-brand-600 shadow-sm'
                          : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 ring-slate-200 dark:ring-slate-700 hover:ring-brand-400 hover:bg-brand-50/50 dark:hover:bg-brand-500/10'"
                        @click="paymentForm.payment_method_id = m.id">
                  <span class="text-base leading-none">{{ PAYMENT_METHOD_ICONS[m.code] || '💰' }}</span>
                  <span>{{ m.name_uz }}</span>
                </button>
              </div>
              <p v-if="!paymentMethods.length" class="mt-1 text-xs text-rose-600">
                To'lov turlari bo'sh — Ma'lumotnomalardan qo'shing
              </p>
            </div>

            <!-- Reference -->
            <div>
              <label class="field-label">Reference (chek raqami)</label>
              <input v-model="paymentForm.reference" class="input font-mono" placeholder="Ixtiyoriy" />
            </div>

            <!-- Receipt -->
            <FileUpload v-model="paymentForm.receipt_file_id"
                        label="Chek (PDF yoki rasm)"
                        hint="Ixtiyoriy. Bank yoki kassa cheki skani"
                        subdir="payments" />

            <!-- Actions -->
            <div class="flex gap-2 pt-2 border-t border-slate-200/70 dark:border-slate-700/40">
              <button class="btn-primary flex-1 !py-2.5" :disabled="paymentSaving" @click="createPayment">
                <CheckCircle2 v-if="!paymentSaving" class="w-4 h-4" />
                {{ paymentSaving ? "Saqlanmoqda..." : "To'lovni saqlash" }}
              </button>
              <button class="btn-ghost !py-2.5" :disabled="paymentSaving" @click="showPaymentForm = false">
                Bekor
              </button>
            </div>
          </div>

          <ul v-if="payments.length" class="space-y-2">
            <li v-for="p in payments" :key="p.id"
                class="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
              <div class="min-w-0">
                <div class="font-mono text-[11px] text-slate-500 dark:text-slate-400">{{ p.payment_number }}</div>
                <div class="font-bold text-slate-900 dark:text-slate-100">{{ fmtMoney(p.amount) }} <span class="text-xs font-medium text-slate-500">so'm</span></div>
                <div class="mt-1 flex items-center gap-2">
                  <span class="pill" :class="
                    p.status === 'confirmed' ? 'pill-success' :
                    p.status === 'failed' ? 'pill-danger' :
                    p.status === 'refunded' ? '' : 'pill-warning'">
                    {{ tr(PAYMENT_STATUS, p.status) }}
                  </span>
                  <span v-if="p.paid_at" class="text-[11px] text-slate-500 dark:text-slate-400">{{ fmtDate(p.paid_at) }}</span>
                </div>
              </div>
              <div class="flex gap-1">
                <button v-if="p.receipt_file_id" class="icon-btn !text-slate-600" title="Chekni ochish"
                        @click="openReceipt(p.receipt_file_id)">
                  <Paperclip class="w-4 h-4" />
                </button>
                <button v-if="p.status === 'pending'" class="icon-btn !text-green-600" title="Tasdiqlash" @click="confirmPayment(p)">
                  <CheckCircle2 class="w-4 h-4" />
                </button>
                <button v-if="p.status === 'confirmed'" class="icon-btn-danger" title="Qaytarish" @click="refundPayment(p)">
                  <RotateCcw class="w-4 h-4" />
                </button>
              </div>
            </li>
          </ul>
          <div v-else class="text-sm text-slate-500 dark:text-slate-400 py-4 text-center">
            Hali to'lovlar yo'q
          </div>
        </section>

        <!-- ========================================================== -->
        <!--   Referral & actor card — who registered / created / etc.   -->
        <!-- ========================================================== -->
        <section class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300">
              <Shield class="w-4 h-4" />
            </span>
            Ariza yo'li
          </h2>

          <ul class="space-y-3 text-sm">
            <!-- Referrer (who invited the applicant) -->
            <li v-if="referralRow" class="flex items-start gap-3">
              <span class="grid place-items-center w-8 h-8 rounded-lg shrink-0 mt-0.5"
                    :class="referralRow.status === 'pending'
                      ? 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300'
                      : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300'">
                <span class="text-base">🎁</span>
              </span>
              <div class="flex-1 min-w-0">
                <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">Kim tavsiya qilgan</div>
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                  {{ actorMap[referralRow.referrer_user_id]?.full_name || actorMap[referralRow.referrer_user_id]?.phone || referralRow.referrer_user_id.slice(0, 8) }}
                </div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  Holat:
                  <strong :class="referralRow.status === 'pending' ? 'text-amber-700 dark:text-amber-300'
                                : referralRow.status === 'active' ? 'text-emerald-700 dark:text-emerald-300'
                                : 'text-slate-700 dark:text-slate-300'">
                    {{ referralRow.status === 'pending' ? 'Kutilmoqda (25% to\'lovga)'
                      : referralRow.status === 'active' ? 'Faol (ishlatish mumkin)'
                      : referralRow.status === 'spent_on_contract' ? 'Chegirma qilingan'
                      : referralRow.status === 'paid_cash' ? 'Naqd to\'langan'
                      : 'Bekor' }}
                  </strong>
                </div>
              </div>
            </li>

            <!-- Registered by -->
            <li class="flex items-start gap-3">
              <span class="grid place-items-center w-8 h-8 rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 shrink-0 mt-0.5">
                <UserIcon class="w-4 h-4" />
              </span>
              <div class="flex-1 min-w-0">
                <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">Kim ro'yxatdan o'tkazgan</div>
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                  <template v-if="applicant?.registered_by_id">
                    {{ actorMap[applicant.registered_by_id]?.full_name || actorMap[applicant.registered_by_id]?.phone || 'Operator' }}
                  </template>
                  <template v-else>Abituriyent o'zi ro'yxatdan o'tgan</template>
                </div>
              </div>
            </li>

            <!-- Reviewer -->
            <li v-if="application.reviewed_by_id" class="flex items-start gap-3">
              <span class="grid place-items-center w-8 h-8 rounded-lg bg-sky-50 text-sky-600 dark:bg-sky-500/15 dark:text-sky-300 shrink-0 mt-0.5">
                <Eye class="w-4 h-4" />
              </span>
              <div class="flex-1 min-w-0">
                <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">Arizani kim ko'rib chiqgan</div>
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                  {{ actorMap[application.reviewed_by_id]?.full_name || actorMap[application.reviewed_by_id]?.phone || application.reviewed_by_id.slice(0, 8) }}
                </div>
                <div v-if="application.reviewed_at" class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  {{ new Date(application.reviewed_at).toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                </div>
              </div>
            </li>

            <!-- Contract creator -->
            <li v-if="contract" class="flex items-start gap-3">
              <span class="grid place-items-center w-8 h-8 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 shrink-0 mt-0.5">
                <FileText class="w-4 h-4" />
              </span>
              <div class="flex-1 min-w-0">
                <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">Shartnomani kim yaratgan</div>
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                  {{ actorMap[contract.created_by_id]?.full_name || actorMap[contract.created_by_id]?.phone || (contract.created_by_id || '—').slice(0, 8) }}
                </div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  Yaratilgan: {{ new Date(contract.created_at).toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                </div>
              </div>
            </li>

            <!-- Contract signed -->
            <li v-if="contract?.signed_at" class="flex items-start gap-3">
              <span class="grid place-items-center w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300 shrink-0 mt-0.5">
                <CheckCircle2 class="w-4 h-4" />
              </span>
              <div class="flex-1 min-w-0">
                <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">Shartnoma imzolangan</div>
                <div class="font-medium text-emerald-700 dark:text-emerald-300">
                  {{ new Date(contract.signed_at).toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                </div>
              </div>
            </li>

            <!-- Lead conversion (if any) -->
            <li v-if="lead && lead.assigned_to_id" class="flex items-start gap-3">
              <span class="grid place-items-center w-8 h-8 rounded-lg bg-violet-50 text-violet-600 dark:bg-violet-500/15 dark:text-violet-300 shrink-0 mt-0.5">
                <Users class="w-4 h-4" />
              </span>
              <div class="flex-1 min-w-0">
                <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">Lead biriktirilgan operator</div>
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                  {{ actorMap[lead.assigned_to_id]?.full_name || actorMap[lead.assigned_to_id]?.phone || lead.assigned_to_name || lead.assigned_to_id.slice(0, 8) }}
                </div>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>
