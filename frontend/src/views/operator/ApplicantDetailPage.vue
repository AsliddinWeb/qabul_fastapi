<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import {
  ArrowLeft, FileText, Save, Award, GraduationCap, Pencil, Gift,
  ArrowRight, Phone, UserPlus, ClipboardList, FileCheck, FileSignature,
  CircleDot, Check, Clock, AlertTriangle,
} from 'lucide-vue-next'
import { staffApi } from '@/api/staff.api'
import type { ApplicantDetailed, ApplicantBase, ApplicantContactStatus } from '@/api/applicants.api'
import {
  APPLICANT_CONTACT_STATUS, APPLICANT_CONTACT_STATUS_TONE, tr,
} from '@/utils/labels'
import { adminApi, type RegionRead, type DistrictRead, type CountryRead } from '@/api/admin.api'
import { referralsApi, type ReferralRead } from '@/api/referrals.api'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import FilePreview from '@/components/ui/FilePreview.vue'
import FileUpload from '@/components/ui/FileUpload.vue'
import {
  PLACEHOLDERS,
  formatNameUpper,
  formatPassport,
  formatPhone,
  formatPinfl,
  passport as vPassport,
  phoneUz as vPhone,
  pinfl as vPinfl,
} from '@/utils/validators'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import LoginInfoCard from '@/components/ui/LoginInfoCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const id = computed(() => route.params.id as string)
const panelPrefix = computed(() => {
  if (route.path.startsWith('/admin/')) return '/admin'
  if (route.path.startsWith('/accountant/')) return '/accountant'
  return '/operator'
})
const isAccountantPanel = computed(() => panelPrefix.value === '/accountant')
const auth = useAuthStore()
const canCreateContract = computed(() => auth.hasPermission('contracts.create'))

const data = ref<ApplicantDetailed | null>(null)
const loading = ref(true)
const saving = ref(false)
const errors = ref<Record<string, string>>({})

// Funnel-stage detection + CRM status. The two are independent:
//   - funnel is COMPUTED from artefacts (diplom / application / contract /
//     signed / paid) — answers "qaysi bosqichda to'xtab qolgan?"
//   - contactStatus is a manual CRM label operators set as they work the
//     candidate. Default 'new', auto → 'enrolled' when contract is signed.
const applications = ref<any[]>([])
const contractsForApplicant = ref<any[]>([])
const contactStatus = ref<ApplicantContactStatus>('new')
const savingStatus = ref(false)

// Diplom + transfer diplom rows for this applicant's user. Same data the
// Application form uses for the inline diplom widget. Loaded lazily after
// the applicant itself arrives so we know the user_id.
const diploms = ref<any[]>([])
const transferDiploms = ref<any[]>([])
const diplomsLoading = ref(false)
async function loadDocs(user_id: string) {
  diplomsLoading.value = true
  try {
    const [d, t] = await Promise.all([
      adminApi.diploms.list({ user_id }).catch(() => ({ items: [] }) as any),
      adminApi.transferDiploms.list({ user_id }).catch(() => ({ items: [] }) as any),
    ])
    diploms.value = (d as any).items || []
    transferDiploms.value = (t as any).items || []
  } finally {
    diplomsLoading.value = false
  }
}

// Referrals — two queries:
//   - referredBy: who invited THIS applicant (filter referred_applicant_id)
//   - invitedByMe: who THIS applicant invited (filter referrer_user_id)
// Loaded in parallel after the applicant arrives.
const referredBy = ref<ReferralRead | null>(null)
const invitedByMe = ref<ReferralRead[]>([])
const referralsLoading = ref(false)
async function loadReferrals(applicant_id: string, user_id: string) {
  referralsLoading.value = true
  try {
    const [inbound, outbound] = await Promise.all([
      referralsApi.list({ referred_applicant_id: applicant_id }).catch(() => [] as ReferralRead[]),
      referralsApi.list({ referrer_user_id: user_id }).catch(() => [] as ReferralRead[]),
    ])
    referredBy.value = inbound[0] || null
    invitedByMe.value = outbound
  } finally {
    referralsLoading.value = false
  }
}

function refTone(s: string): string {
  if (s === 'active' || s === 'spent_on_contract' || s === 'paid_cash')
    return 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300'
  if (s === 'pending')
    return 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300'
  return 'bg-slate-100 text-slate-600 ring-slate-200 dark:bg-slate-800 dark:text-slate-400'
}
function refLabel(s: string): string {
  return {
    pending: 'Kutilmoqda',
    active: 'Faol',
    spent_on_contract: 'Shartnomaga ishlatildi',
    paid_cash: 'Naqd olingan',
    cancelled: 'Bekor qilingan',
  }[s] || s
}

const personal = reactive<ApplicantBase>({
  last_name: '', first_name: '', other_name: '',
  birth_date: '', gender: 'male',
  passport_series: '', pinfl: '',
  region_id: null, district_id: null,
  address: '', nationality: "O'zbek",
  additional_phone: '', telegram_username: '',
  // Optional passport scan — PDF or image. nullable in the DB,
  // SET NULL on cascade, so removing it just clears the FK.
  passport_file_id: null,
})

const countries = ref<CountryRead[]>([])
const regions = ref<RegionRead[]>([])
const districts = ref<DistrictRead[]>([])

async function load() {
  loading.value = true
  try {
    data.value = await staffApi.applicants.get(id.value)
    Object.assign(personal, {
      last_name: data.value.last_name,
      first_name: data.value.first_name,
      other_name: data.value.other_name || '',
      birth_date: data.value.birth_date,
      gender: data.value.gender,
      passport_series: data.value.passport_series || '',
      pinfl: data.value.pinfl || '',
      region_id: data.value.region_id || null,
      district_id: data.value.district_id || null,
      address: data.value.address || '',
      nationality: data.value.nationality || "O'zbek",
      additional_phone: data.value.additional_phone || '',
      telegram_username: (data.value as any).telegram_username || '',
      passport_file_id: data.value.passport_file_id || null,
    })
    contactStatus.value = ((data.value as any).contact_status as ApplicantContactStatus) || 'new'
  } finally {
    loading.value = false
  }
}

/**
 * Fetch this applicant's applications + their contracts so the funnel
 * timeline can show what's done vs what's missing. Both calls are
 * fire-and-forget — failures leave the chip muted instead of blocking
 * the page.
 */
async function loadFunnelArtefacts(applicant_id: string) {
  try {
    const apps = await staffApi.applications.list({
      applicant_id, page: 1, size: 50,
    } as any)
    applications.value = apps.items || []
    // Pull contracts per application in parallel. Most applicants have
    // 0-1 contracts so this is cheap.
    const all = await Promise.all(
      applications.value.map((a: any) =>
        adminApi.contracts.list({ application_id: a.id, size: 50 })
          .then((r: any) => r.items || [])
          .catch(() => []),
      ),
    )
    contractsForApplicant.value = all.flat()
  } catch {
    /* ignore — funnel sections fall back to "Bajarilmagan" placeholders */
  }
}

/** Persist the CRM status pill. Optimistic — UI flips immediately. */
async function saveContactStatus(next: ApplicantContactStatus) {
  if (!data.value) return
  const prev = contactStatus.value
  contactStatus.value = next
  savingStatus.value = true
  try {
    await staffApi.applicants.update(data.value.id, { contact_status: next } as any)
    toast.success(`Holati: ${tr(APPLICANT_CONTACT_STATUS, next)}`)
  } catch (e) {
    contactStatus.value = prev
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'zgartirib bo'lmadi")
  } finally {
    savingStatus.value = false
  }
}

/**
 * Funnel stages — top to bottom. Each carries:
 *   - done: did this step happen?
 *   - hint: what's needed to unstick (only shown for the first
 *           not-done step, so the operator sees ONE actionable item)
 */
interface FunnelStep {
  key: string
  label: string
  icon: any
  done: boolean
  hint: string
  href?: string
}
const funnelSteps = computed<FunnelStep[]>(() => {
  if (!data.value) return []
  const hasDiplom = diploms.value.length > 0 || transferDiploms.value.length > 0
  const hasApp = applications.value.length > 0
  const acceptedApp = applications.value.find((a: any) => a.status === 'qabul_qilindi')
  const activeContract = contractsForApplicant.value.find((c: any) => c.status !== 'cancelled')
  const signedContract = contractsForApplicant.value.find((c: any) => c.status === 'signed')
  const paidContract = contractsForApplicant.value.find((c: any) =>
    Number(c.paid_amount || 0) > 0,
  )
  const base = panelPrefix.value
  return [
    {
      key: 'registered',
      label: "Profil ro'yxatdan o'tdi",
      icon: UserPlus,
      done: true,
      hint: '',
    },
    {
      key: 'diplom',
      label: 'Diplom kiritildi',
      icon: GraduationCap,
      done: hasDiplom,
      hint: "Diplom hali kiritilmagan — pastdagi 'Hujjatlar' bo'limidan qo'shing.",
    },
    {
      key: 'application',
      label: 'Ariza topshirildi',
      icon: ClipboardList,
      done: hasApp,
      hint: 'Ariza topshirilmagan — yangi ariza yaratib qo\'shing.',
      href: `${base}/applications/new?applicant_id=${data.value.id}`,
    },
    {
      key: 'accepted',
      label: 'Ariza qabul qilindi',
      icon: FileCheck,
      done: !!acceptedApp,
      hint: 'Ariza hali ko\'rib chiqilmadi yoki rad etildi.',
      href: hasApp ? `${base}/applications/${applications.value[0].id}` : undefined,
    },
    {
      key: 'contract',
      label: 'Shartnoma yaratildi',
      icon: FileText,
      done: !!activeContract,
      hint: 'Qabul qilingan ariza uchun shartnoma yaratish kerak.',
    },
    {
      key: 'signed',
      label: 'Shartnoma imzolandi',
      icon: FileSignature,
      done: !!signedContract,
      hint: "Shartnoma loyiha holatida — imzolash kerak.",
    },
    {
      key: 'paid',
      label: "To'lov boshlandi",
      icon: Check,
      done: !!paidContract,
      hint: "Birinchi to'lov hali kelmadi.",
    },
  ]
})
const currentBlocker = computed<FunnelStep | null>(() => funnelSteps.value.find(s => !s.done) || null)
const lastCompletedIdx = computed(() => {
  const done = funnelSteps.value.findLastIndex?.((s: any) => s.done)
  if (done !== undefined && done >= 0) return done
  let last = -1
  funnelSteps.value.forEach((s, i) => { if (s.done) last = i })
  return last
})

onMounted(async () => {
  countries.value = await adminApi.countries.list().catch(() => [])
  const uz = countries.value.find((c) => c.name === "O'zbekiston") || countries.value[0]
  if (uz) regions.value = await adminApi.regions.list(uz.id).catch(() => [])
  await load()
  if (personal.region_id) {
    districts.value = await adminApi.districts.list(personal.region_id).catch(() => [])
  }
  if (data.value?.user_id) {
    // Don't block initial paint — diplom, referral, and funnel fetches
    // are independent and the page renders progressively.
    loadDocs(data.value.user_id)
    loadReferrals(data.value.id, data.value.user_id)
    loadFunnelArtefacts(data.value.id)
  }
})

watch(() => personal.region_id, async (rid) => {
  if (rid) districts.value = await adminApi.districts.list(rid).catch(() => [])
  else districts.value = []
})

// Real-time format + validate
function validateField(field: string) {
  const ne = { ...errors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'last_name':       err = personal.last_name.trim() ? null : 'Familiya majburiy'; break
    case 'first_name':      err = personal.first_name.trim() ? null : 'Ism majburiy'; break
    case 'birth_date':      err = personal.birth_date ? null : "Tug'ilgan sana majburiy"; break
    case 'passport_series': err = vPassport(personal.passport_series || ''); break
    case 'pinfl':           err = vPinfl(personal.pinfl || ''); break
    case 'additional_phone':err = personal.additional_phone ? vPhone(personal.additional_phone) : null; break
    case 'telegram_username':
      err = personal.telegram_username && !/^[a-zA-Z][a-zA-Z0-9_]{3,31}$/.test(personal.telegram_username.replace(/^@/, ''))
        ? "Faqat lotin harf, raqam va _ (4-32 belgi)"
        : null
      break
  }
  if (err) ne[field] = err
  errors.value = ne
}

function onLast(e: Event)     { personal.last_name = formatNameUpper((e.target as HTMLInputElement).value); validateField('last_name') }
function onFirst(e: Event)    { personal.first_name = formatNameUpper((e.target as HTMLInputElement).value); validateField('first_name') }
function onOther(e: Event)    { personal.other_name = formatNameUpper((e.target as HTMLInputElement).value) }
function onPassport(e: Event) { personal.passport_series = formatPassport((e.target as HTMLInputElement).value); validateField('passport_series') }
function onPinfl(e: Event)    { personal.pinfl = formatPinfl((e.target as HTMLInputElement).value); validateField('pinfl') }
function onAddPhone(e: Event) { personal.additional_phone = formatPhone((e.target as HTMLInputElement).value); validateField('additional_phone') }

function validateAll(): boolean {
  ;['last_name', 'first_name', 'birth_date', 'passport_series', 'pinfl', 'additional_phone', 'telegram_username'].forEach(validateField)
  return Object.keys(errors.value).length === 0
}

async function saveInfo() {
  if (!validateAll()) {
    toast.error("Maydonlarni to'g'ri to'ldiring")
    return
  }
  saving.value = true
  try {
    const payload = {
      ...personal,
      telegram_username: personal.telegram_username ? personal.telegram_username.trim().replace(/^@/, '') : null,
    }
    await staffApi.applicants.update(id.value, payload as any)
    toast.success('Saqlandi')
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || 'Xatolik')
  } finally {
    saving.value = false
  }
}

async function generateContract() {
  const list = await staffApi.applications.list({
    applicant_id: id.value,
    status: 'qabul_qilindi',
    page: 1,
    size: 1,
  })
  if (!list.items.length) {
    toast.error("Avval ariza qabul qilinishi kerak (status: qabul_qilindi)")
    return
  }
  router.push({
    path: `${panelPrefix.value}/contracts/new`,
    query: { application: list.items[0].id },
  })
}
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="data" class="space-y-6">
    <PageHeader
      :title="`${data.last_name} ${data.first_name} ${data.other_name || ''}`.trim()"
      :subtitle="`ID: ${data.id}`"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'Abituriyentlar', to: panelPrefix + '/applicants' }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
      <button v-if="!isAccountantPanel && canCreateContract" class="btn-primary" @click="generateContract">
        <FileText class="w-4 h-4" /> Shartnoma yaratish
      </button>
    </PageHeader>

    <!-- ===== Funnel + CRM status — top of detail page =====
         Tells the operator at a glance:
           1. Which step in the application-contract pipeline the
              candidate is at (or stuck at).
           2. Their current CRM funnel label (Yangi / Gaplashildi / …).
         The blocker pill ("Bosqich: <next-step>") is the actionable
         summary; the dropdown is the manual override. -->
    <section class="card p-4 sm:p-6 space-y-4">
      <div class="flex items-start justify-between gap-3 flex-wrap">
        <div class="min-w-0 flex-1">
          <h3 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
            <CircleDot class="w-4 h-4 text-brand-600" /> Holat va bosqich
          </h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            <span v-if="currentBlocker" class="inline-flex items-center gap-1">
              <Clock class="w-3 h-3 text-amber-500" />
              Bosqich: <strong class="text-amber-700 dark:text-amber-300">{{ currentBlocker.label }}</strong>
            </span>
            <span v-else class="inline-flex items-center gap-1">
              <Check class="w-3 h-3 text-emerald-500" />
              Hamma bosqichlar tugallandi
            </span>
          </p>
        </div>
        <!-- CRM status dropdown — only writable on non-accountant panels -->
        <div class="shrink-0">
          <label class="block text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1">
            CRM holati
          </label>
          <div class="inline-flex items-center gap-2">
            <select
              :value="contactStatus"
              :disabled="isAccountantPanel || savingStatus"
              class="input !py-1.5 !text-xs font-semibold !w-auto"
              :class="APPLICANT_CONTACT_STATUS_TONE[contactStatus]"
              @change="saveContactStatus(($event.target as HTMLSelectElement).value as ApplicantContactStatus)">
              <option v-for="(label, val) in APPLICANT_CONTACT_STATUS" :key="val" :value="val">
                {{ label }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- Funnel stepper — horizontal on desktop, vertical on mobile.
           Done steps glow emerald; the FIRST not-done step is amber
           (the blocker); subsequent not-done steps stay muted. -->
      <ol class="grid grid-cols-1 sm:grid-cols-7 gap-2">
        <li v-for="(s, i) in funnelSteps" :key="s.key"
            class="flex sm:flex-col items-center sm:items-stretch gap-2 sm:gap-1 p-2 rounded-lg ring-1"
            :class="s.done
              ? 'ring-emerald-200/60 dark:ring-emerald-700/30 bg-emerald-50/40 dark:bg-emerald-500/10'
              : i === lastCompletedIdx + 1
                ? 'ring-amber-200/60 dark:ring-amber-700/30 bg-amber-50/40 dark:bg-amber-500/10'
                : 'ring-slate-200/60 dark:ring-slate-700/40 bg-slate-50/40 dark:bg-slate-800/30 opacity-70'">
          <div class="grid place-items-center w-8 h-8 rounded-lg shrink-0"
               :class="s.done
                 ? 'bg-emerald-500 text-white'
                 : i === lastCompletedIdx + 1
                   ? 'bg-amber-500 text-white'
                   : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400'">
            <component :is="s.done ? Check : s.icon" class="w-4 h-4" />
          </div>
          <div class="min-w-0 sm:text-center">
            <div class="text-[11px] font-semibold leading-snug"
                 :class="s.done
                   ? 'text-emerald-700 dark:text-emerald-300'
                   : i === lastCompletedIdx + 1
                     ? 'text-amber-700 dark:text-amber-300'
                     : 'text-slate-500 dark:text-slate-400'">
              {{ s.label }}
            </div>
          </div>
        </li>
      </ol>

      <!-- Single, actionable hint for the current blocker — keeps the
           operator's attention on ONE thing to do next. -->
      <div v-if="currentBlocker && currentBlocker.hint"
           class="flex items-start gap-2 p-3 rounded-lg bg-amber-50/60 dark:bg-amber-500/10 ring-1 ring-amber-200/60 dark:ring-amber-700/30 text-xs text-amber-800 dark:text-amber-300">
        <AlertTriangle class="w-3.5 h-3.5 mt-0.5 shrink-0" />
        <div class="flex-1">
          {{ currentBlocker.hint }}
          <RouterLink v-if="currentBlocker.href" :to="currentBlocker.href"
                      class="ml-2 inline-flex items-center gap-1 font-semibold text-brand-700 dark:text-brand-300 hover:underline">
            Sahifaga o'tish <ArrowRight class="w-3 h-3" />
          </RouterLink>
        </div>
      </div>
    </section>

    <section class="card p-4 sm:p-6 space-y-4">
      <h3 class="font-semibold text-slate-900 dark:text-slate-100">Shaxsiy ma'lumotlar</h3>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Familiya *</label>
          <input :value="personal.last_name" class="input" placeholder="VALIYEV"
                 :class="errors.last_name ? 'border-red-500' : ''"
                 @input="onLast" @blur="validateField('last_name')" />
          <p v-if="errors.last_name" class="mt-1 text-xs text-red-600">{{ errors.last_name }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Ism *</label>
          <input :value="personal.first_name" class="input" placeholder="ALI"
                 :class="errors.first_name ? 'border-red-500' : ''"
                 @input="onFirst" @blur="validateField('first_name')" />
          <p v-if="errors.first_name" class="mt-1 text-xs text-red-600">{{ errors.first_name }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Otasining ismi</label>
          <input :value="personal.other_name" class="input" placeholder="AKBAR O'G'LI" @input="onOther" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Tug'ilgan sana *</label>
          <input v-model="personal.birth_date" type="date" class="input"
                 :class="errors.birth_date ? 'border-red-500' : ''"
                 :max="new Date().toISOString().slice(0,10)"
                 @blur="validateField('birth_date')" />
          <p v-if="errors.birth_date" class="mt-1 text-xs text-red-600">{{ errors.birth_date }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Jinsi *</label>
          <select v-model="personal.gender" class="input">
            <option value="male">Erkak</option>
            <option value="female">Ayol</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Millati</label>
          <input v-model="personal.nationality" class="input" placeholder="O'zbek" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Pasport seriyasi</label>
          <input :value="personal.passport_series" class="input font-mono" maxlength="9"
                 :class="errors.passport_series ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.passport"
                 @input="onPassport" @blur="validateField('passport_series')" />
          <p v-if="errors.passport_series" class="mt-1 text-xs text-red-600">{{ errors.passport_series }}</p>
          <p v-else class="mt-1 text-xs text-slate-500 dark:text-slate-400">2 lotin harf + 7 raqam</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">JSHSHIR (PINFL)</label>
          <input :value="personal.pinfl" class="input font-mono" inputmode="numeric" maxlength="14"
                 :class="errors.pinfl ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.pinfl"
                 @input="onPinfl" @blur="validateField('pinfl')" />
          <p v-if="errors.pinfl" class="mt-1 text-xs text-red-600">{{ errors.pinfl }}</p>
          <p v-else class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ (personal.pinfl || '').length }}/14</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Qo'shimcha telefon</label>
          <input :value="personal.additional_phone" type="tel" inputmode="tel"
                 class="input font-mono"
                 :class="errors.additional_phone ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.phoneUz"
                 @input="onAddPhone" @blur="validateField('additional_phone')" />
          <p v-if="errors.additional_phone" class="mt-1 text-xs text-red-600">{{ errors.additional_phone }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Telegram username</label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-mono pointer-events-none">@</span>
            <input v-model="personal.telegram_username" class="input pl-7 font-mono"
                   :class="errors.telegram_username ? 'border-red-500' : ''"
                   placeholder="username"
                   @blur="validateField('telegram_username')" />
          </div>
          <p v-if="errors.telegram_username" class="mt-1 text-xs text-red-600">{{ errors.telegram_username }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Viloyat</label>
          <select v-model="personal.region_id" class="input">
            <option :value="null">— tanlang —</option>
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Tuman</label>
          <select v-model="personal.district_id" class="input" :disabled="!personal.region_id">
            <option :value="null">— tanlang —</option>
            <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <div class="sm:col-span-2 lg:col-span-3 xl:col-span-4">
          <label class="block text-sm font-medium mb-1">Manzil</label>
          <input v-model="personal.address" class="input" placeholder="Mahalla yoki ko'cha nomi, uy raqami" />
        </div>
        <!-- Passport scan — optional. PDF or image. The DB FK is SET NULL
             on delete so removing the file just clears the reference; the
             actual bytes stay in /files until a separate vacuum job runs. -->
        <div class="sm:col-span-2 lg:col-span-3 xl:col-span-4">
          <FileUpload
            :model-value="personal.passport_file_id ?? null"
            @update:model-value="(v: string | null) => personal.passport_file_id = v"
            label="Pasport (skani yoki rasm) — ixtiyoriy"
            hint="PDF yoki rasm (JPG/PNG/WEBP). Pasport sahifasining toza skani / rasmi"
            subdir="passports" />
        </div>
      </div>
      <button v-if="!isAccountantPanel" class="btn-primary" :disabled="saving" @click="saveInfo">
        <Save class="w-4 h-4" /> {{ saving ? 'Saqlanmoqda...' : 'Saqlash' }}
      </button>
    </section>

    <!-- Login info card -->
    <LoginInfoCard v-if="data?.user_id" :user-id="data.user_id" />

    <!-- Diplom + perevod diplomi hujjatlari. Loaded async (don't block
         the personal-info form), shows a skeleton placeholder while the
         GET /diploms?user_id query is in flight. Each row uses
         FilePreview which fetches /files/{id}/meta and renders the
         right kind of tile (image thumbnail / PDF / generic). -->
    <section class="card p-4 sm:p-6">
      <div class="flex items-center gap-2 mb-4">
        <span class="grid place-items-center w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300">
          <Award class="w-4 h-4" />
        </span>
        <h3 class="font-semibold text-slate-900 dark:text-slate-100">Hujjatlar</h3>
      </div>

      <div v-if="diplomsLoading" class="text-sm text-slate-500 dark:text-slate-400">
        Yuklanmoqda...
      </div>

      <div v-else-if="!diploms.length && !transferDiploms.length"
           class="rounded-lg border border-dashed border-slate-200 dark:border-slate-700 p-6 text-center">
        <FileText class="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Bu abituriyentda diplom ham, perevod diplomi ham yo'q.
        </p>
      </div>

      <div v-else class="space-y-5">
        <!-- 1-kurs diploms -->
        <div v-if="diploms.length">
          <div class="flex items-center justify-between mb-2">
            <div class="text-sm font-semibold text-slate-700 dark:text-slate-300 inline-flex items-center gap-1.5">
              <GraduationCap class="w-4 h-4" /> Diplom (1-kurs uchun)
            </div>
            <span class="text-[11px] text-slate-400 dark:text-slate-500">{{ diploms.length }} ta</span>
          </div>
          <div class="grid sm:grid-cols-2 gap-3">
            <div v-for="d in diploms" :key="d.id"
                 class="rounded-xl ring-1 ring-slate-200 dark:ring-slate-700 p-3 space-y-2 bg-slate-50/40 dark:bg-slate-900/30">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0 flex-1">
                  <div class="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">{{ d.university_name || '—' }}</div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    <span class="font-mono">{{ d.serial_number }}</span>
                    <span v-if="d.graduation_year"> · {{ d.graduation_year }}</span>
                  </div>
                </div>
                <RouterLink v-if="!isAccountantPanel" :to="`${panelPrefix}/diploms/${d.id}`"
                            class="icon-btn !w-7 !h-7" title="Tahrirlash">
                  <Pencil class="w-3.5 h-3.5" />
                </RouterLink>
              </div>
              <FilePreview :file-id="d.diploma_file_id" size="compact" />
            </div>
          </div>
        </div>

        <!-- Perevod diploms -->
        <div v-if="transferDiploms.length">
          <div class="flex items-center justify-between mb-2">
            <div class="text-sm font-semibold text-slate-700 dark:text-slate-300 inline-flex items-center gap-1.5">
              <GraduationCap class="w-4 h-4" /> Perevod diplomi
            </div>
            <span class="text-[11px] text-slate-400 dark:text-slate-500">{{ transferDiploms.length }} ta</span>
          </div>
          <div class="grid sm:grid-cols-2 gap-3">
            <div v-for="t in transferDiploms" :key="t.id"
                 class="rounded-xl ring-1 ring-slate-200 dark:ring-slate-700 p-3 space-y-2 bg-slate-50/40 dark:bg-slate-900/30">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0 flex-1">
                  <div class="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">{{ t.university_name || '—' }}</div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    Transkript fayli
                  </div>
                </div>
                <RouterLink v-if="!isAccountantPanel" :to="`${panelPrefix}/transfer-diploms/${t.id}`"
                            class="icon-btn !w-7 !h-7" title="Tahrirlash">
                  <Pencil class="w-3.5 h-3.5" />
                </RouterLink>
              </div>
              <FilePreview :file-id="t.transcript_file_id" size="compact" />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Referal dasturi. Two halves:
         · Who invited THIS applicant (at most 1)
         · Who THIS applicant invited (list)
         Hidden entirely when both halves are empty — there's no value
         in showing an empty "no referrals" card on every profile. -->
    <section v-if="referralsLoading || referredBy || invitedByMe.length"
             class="card p-4 sm:p-6">
      <div class="flex items-center gap-2 mb-4">
        <span class="grid place-items-center w-8 h-8 rounded-lg bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300">
          <Gift class="w-4 h-4" />
        </span>
        <h3 class="font-semibold text-slate-900 dark:text-slate-100">Referal dasturi</h3>
      </div>

      <div v-if="referralsLoading" class="text-sm text-slate-500 dark:text-slate-400">
        Yuklanmoqda...
      </div>

      <template v-else>
        <!-- Inbound: who invited this applicant -->
        <div v-if="referredBy" class="mb-5">
          <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
            Bu abituriyentni kim taklif qildi
          </div>
          <div class="rounded-xl ring-1 ring-rose-200 dark:ring-rose-700/40 bg-rose-50/50 dark:bg-rose-500/5 p-3 flex items-center gap-3 flex-wrap">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-rose-500 to-pink-500 text-white grid place-items-center font-semibold text-sm shrink-0">
              {{ (referredBy.referrer_full_name || '?').slice(0, 1).toUpperCase() }}
            </div>
            <div class="min-w-0 flex-1">
              <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                {{ referredBy.referrer_full_name || `User ${referredBy.referrer_user_id.slice(0, 8)}` }}
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 inline-flex items-center gap-1.5 font-mono mt-0.5">
                <Phone class="w-3 h-3" />
                {{ referredBy.referrer_phone || '—' }}
              </div>
            </div>
            <span class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold ring-1"
                  :class="refTone(referredBy.status)">
              {{ refLabel(referredBy.status) }}
            </span>
          </div>
        </div>

        <!-- Outbound: who this applicant invited -->
        <div v-if="invitedByMe.length">
          <div class="flex items-center justify-between mb-1.5">
            <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Bu abituriyent taklif qilgan ({{ invitedByMe.length }})
            </div>
          </div>
          <ul class="rounded-xl ring-1 ring-slate-200 dark:ring-slate-700 divide-y divide-slate-100 dark:divide-slate-800 overflow-hidden">
            <li v-for="r in invitedByMe" :key="r.id"
                class="p-3 flex items-center gap-3 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
              <div class="w-9 h-9 rounded-full bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center text-xs font-semibold shrink-0">
                {{ (r.referred_full_name || '?').slice(0, 1).toUpperCase() }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">
                  {{ r.referred_full_name || `Applicant ${r.referred_applicant_id.slice(0, 8)}` }}
                </div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 inline-flex items-center gap-1.5 font-mono mt-0.5">
                  <Phone class="w-3 h-3" />
                  {{ r.referred_phone || '—' }}
                </div>
              </div>
              <RouterLink :to="`${panelPrefix}/applicants/${r.referred_applicant_id}`"
                          class="icon-btn !w-7 !h-7" title="Bu abituriyent sahifasi">
                <ArrowRight class="w-3.5 h-3.5" />
              </RouterLink>
              <span class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-semibold ring-1 shrink-0"
                    :class="refTone(r.status)">
                {{ refLabel(r.status) }}
              </span>
            </li>
          </ul>
        </div>
      </template>
    </section>
  </div>
</template>
