<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import {
  Save, User as UserIcon, IdCard, GraduationCap, ClipboardList, Check,
  ArrowRight, ArrowLeft, AlertCircle, CheckCircle2, Loader2,
} from 'lucide-vue-next'
import FileUpload from '@/components/ui/FileUpload.vue'
import {
  applicantsApi,
  type ApplicantBase,
  type ApplicantDetailed,
} from '@/api/applicants.api'
import { applicationsApi, type AdmissionType } from '@/api/applications.api'
import {
  adminApi,
  type RegionRead, type DistrictRead, type CountryRead,
  type NamedRecord,
} from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'

const toast = useToast()
const router = useRouter()
const auth = useAuthStore()

// ===========================================================================
// Step machine
// ===========================================================================
type StepKey = 'profile' | 'diplom' | 'application'
const currentStep = ref<StepKey>('profile')

const profile = ref<ApplicantDetailed | null>(null)
const myApplications = ref<{ id: string }[]>([])
const initialLoading = ref(true)

const stepStatus = computed(() => ({
  profile: !!(profile.value?.last_name && profile.value?.first_name &&
              profile.value?.birth_date && profile.value?.passport_series &&
              profile.value?.pinfl),
  diplom: !!(profile.value?.diplom || profile.value?.transfer_diplom),
  application: myApplications.value.length > 0,
}))

const stepDefs: { key: StepKey; title: string; icon: any }[] = [
  { key: 'profile',     title: "Shaxsiy ma'lumotlar va pasport", icon: UserIcon },
  { key: 'diplom',      title: 'Diplom yoki attestat',           icon: GraduationCap },
  { key: 'application', title: "Yo'nalishga ariza",              icon: ClipboardList },
]

function gotoStep(s: StepKey) {
  currentStep.value = s
  errors.value = {}
  scrollToTop()
}
function scrollToTop() {
  if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ===========================================================================
// Step 1 — Personal + passport (merged)
// ===========================================================================
const personal = reactive<ApplicantBase>({
  last_name: '', first_name: '', other_name: '',
  birth_date: '', gender: 'male',
  passport_series: '', pinfl: '',
  region_id: null, district_id: null,
  address: '', nationality: "O'zbek",
  additional_phone: '', email: null,
})
const errors = ref<Record<string, string>>({})
const savingProfile = ref(false)

const countries = ref<CountryRead[]>([])
const regions = ref<RegionRead[]>([])
const districts = ref<DistrictRead[]>([])

watch(() => personal.region_id, async (rid) => {
  districts.value = rid ? await adminApi.districts.list(rid).catch(() => []) : []
  if (!districts.value.find(d => d.id === personal.district_id)) {
    personal.district_id = null
  }
})

function validatePersonal(): boolean {
  const e: Record<string, string> = {}
  const ln = personal.last_name?.trim() || ''
  const fn = personal.first_name?.trim() || ''
  if (!ln) e.last_name = 'Familiyani kiriting'
  else if (ln.length < 2) e.last_name = 'Familiya juda qisqa'
  if (!fn) e.first_name = 'Ismni kiriting'
  else if (fn.length < 2) e.first_name = 'Ism juda qisqa'

  if (!personal.birth_date) e.birth_date = "Tug'ilgan sanani tanlang"
  else {
    const d = new Date(personal.birth_date)
    const now = new Date()
    if (isNaN(d.getTime())) e.birth_date = "Sana noto'g'ri"
    else if (d > now) e.birth_date = 'Kelajakdagi sana bo\'la olmaydi'
    else {
      const age = Math.floor((now.getTime() - d.getTime()) / (365.25 * 24 * 3600 * 1000))
      if (age < 14) e.birth_date = `Yosh kichik (${age}). Kamida 14 yosh bo'lishi kerak`
      if (age > 100) e.birth_date = "Sanani qaytadan tekshiring"
    }
  }

  if (!personal.gender) e.gender = 'Jinsni tanlang'

  const ps = (personal.passport_series || '').toUpperCase().trim()
  if (!ps) e.passport_series = 'Pasport seriyasi va raqamini kiriting'
  else if (!/^[A-Z]{2}\d{7}$/.test(ps)) e.passport_series = "Format: AA1234567 (2 harf + 7 raqam)"

  const pi = (personal.pinfl || '').trim()
  if (!pi) e.pinfl = 'JSHSHIR (PINFL)ni kiriting'
  else if (!/^\d{14}$/.test(pi)) e.pinfl = '14 ta raqamdan iborat bo\'lishi kerak'

  if (personal.email && personal.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(personal.email.trim())) {
    e.email = "Email noto'g'ri"
  }
  if (personal.additional_phone && personal.additional_phone.trim()) {
    const ap = personal.additional_phone.replace(/\s|-/g, '')
    if (!/^\+998\d{9}$/.test(ap)) e.additional_phone = "Format: +998 XX XXX XX XX"
  }

  errors.value = e
  return Object.keys(e).length === 0
}

async function saveProfile() {
  if (!validatePersonal()) {
    toast.error("Maydonlardagi xatolarni tuzating")
    return
  }
  savingProfile.value = true
  try {
    const payload = {
      ...personal,
      passport_series: (personal.passport_series || '').toUpperCase().trim(),
      pinfl: (personal.pinfl || '').trim(),
      additional_phone: personal.additional_phone?.replace(/\s|-/g, '') || null,
      email: personal.email?.trim() || null,
    }
    if (profile.value) await applicantsApi.updateMe(payload)
    else                 await applicantsApi.createMe(payload)
    toast.success("Ma'lumotlar saqlandi")
    await loadInitial()
    gotoStep('diplom')
  } catch (e) {
    handleApiError(e)
  } finally {
    savingProfile.value = false
  }
}

// ===========================================================================
// Step 2 — Diplom (1-kurs / perevod)
// ===========================================================================
const admissionType = ref<AdmissionType>('yangi_qabul')

// 1-kurs (diplom) form
const diplom = reactive({
  serial_number: '',
  education_type_id: '',
  institution_type_id: '',
  university_name: '',
  graduation_year: String(new Date().getFullYear()),
  region_id: '',
  district_id: '',
  diploma_file_id: null as string | null,
})
const diplomDistricts = ref<DistrictRead[]>([])
watch(() => diplom.region_id, async (rid) => {
  diplomDistricts.value = rid ? await adminApi.districts.list(rid).catch(() => []) : []
  if (!diplomDistricts.value.find(d => d.id === diplom.district_id)) diplom.district_id = ''
})

// Transfer diplom form
const transferDiplom = reactive({
  country_id: '',
  university_name: '',
  target_course_id: '',
  transcript_file_id: null as string | null,
})

const educationTypes = ref<NamedRecord[]>([])
const institutionTypes = ref<NamedRecord[]>([])
const courses = ref<NamedRecord[]>([])
const savingDiplom = ref(false)

function validateDiplom(): boolean {
  const e: Record<string, string> = {}
  if (admissionType.value === 'yangi_qabul') {
    if (!diplom.serial_number.trim()) e.diplom_series = "Diplom yoki shahodatnoma seriyasini kiriting"
    if (!diplom.education_type_id) e.education_type_id = "Hujjat turini tanlang"
    if (!diplom.institution_type_id) e.institution_type_id = "Muassasa turini tanlang"
    if (!diplom.university_name.trim()) e.university_name = "Muassasa nomini kiriting"
    if (!/^\d{4}$/.test(diplom.graduation_year)) e.graduation_year = "Yili: 4 raqam (masalan 2024)"
    else {
      const y = parseInt(diplom.graduation_year, 10)
      const now = new Date().getFullYear()
      if (y < 1970 || y > now + 1) e.graduation_year = `Yil ${1970}–${now + 1} oralig'ida bo'lsin`
    }
    if (!diplom.region_id) e.region_id = "Viloyatni tanlang"
    if (!diplom.district_id) e.district_id = "Tumanni tanlang"
    if (!diplom.diploma_file_id) e.diploma_file_id = "Diplom yoki shahodatnoma faylini yuklang"
  } else {
    if (!transferDiplom.country_id) e.country_id = "Davlatni tanlang"
    if (!transferDiplom.university_name.trim()) e.university_name = "Muassasa nomini kiriting"
    if (!transferDiplom.target_course_id) e.target_course_id = "Kursni tanlang"
    if (!transferDiplom.transcript_file_id) e.transcript_file_id = "Transkript faylini yuklang"
  }
  errors.value = e
  return Object.keys(e).length === 0
}

async function saveDiplom() {
  if (!validateDiplom()) {
    toast.error("Maydonlardagi xatolarni tuzating")
    return
  }
  savingDiplom.value = true
  try {
    const userId = auth.user?.id || ''
    if (admissionType.value === 'yangi_qabul') {
      await applicantsApi.upsertDiplom({ ...diplom, user_id: userId })
    } else {
      await applicantsApi.upsertTransferDiplom({ ...transferDiplom, user_id: userId })
    }
    toast.success("Diplom ma'lumotlari saqlandi")
    await loadInitial()
    gotoStep('application')
  } catch (e) {
    handleApiError(e)
  } finally {
    savingDiplom.value = false
  }
}

// ===========================================================================
// Step 3 — Application (program selection)
// ===========================================================================
const branches = ref<NamedRecord[]>([])
const educationLevels = ref<NamedRecord[]>([])
const educationForms = ref<NamedRecord[]>([])
const programs = ref<Array<NamedRecord & {
  branch_id: string; education_level_id: string; education_form_id: string;
  tuition_fee: number; study_duration_years: number; is_active: boolean;
}>>([])

const application = reactive({
  branch_id: '',
  education_level_id: '',
  education_form_id: '',
  program_id: '',
  notes: '',
})
const submittingApp = ref(false)

const filteredForms = computed(() => {
  // For 1-kurs (yangi qabul) only Kunduzgi is allowed.
  if (admissionType.value === 'yangi_qabul') {
    return educationForms.value.filter(f => f.name?.toLowerCase().includes('kunduz'))
  }
  return educationForms.value
})

const filteredPrograms = computed(() => {
  return programs.value.filter(p =>
    (!application.branch_id || p.branch_id === application.branch_id) &&
    (!application.education_level_id || p.education_level_id === application.education_level_id) &&
    (!application.education_form_id || p.education_form_id === application.education_form_id) &&
    p.is_active,
  )
})

watch(filteredPrograms, (list) => {
  if (application.program_id && !list.find(p => p.id === application.program_id)) {
    application.program_id = ''
  }
})

watch(filteredForms, (list) => {
  if (application.education_form_id && !list.find(f => f.id === application.education_form_id)) {
    application.education_form_id = list[0]?.id || ''
  } else if (!application.education_form_id && list.length === 1) {
    application.education_form_id = list[0].id
  }
})

function validateApplication(): boolean {
  const e: Record<string, string> = {}
  if (!application.branch_id) e.branch_id = 'Filialni tanlang'
  if (!application.education_level_id) e.education_level_id = "Ta'lim darajasini tanlang"
  if (!application.education_form_id) e.education_form_id = "Ta'lim shaklini tanlang"
  if (!application.program_id) e.program_id = "Yo'nalishni tanlang"
  errors.value = e
  return Object.keys(e).length === 0
}

async function submitApplication() {
  if (!validateApplication()) {
    toast.error("Maydonlardagi xatolarni tuzating")
    return
  }
  submittingApp.value = true
  try {
    const payload: any = {
      admission_type: admissionType.value,
      branch_id: application.branch_id,
      education_level_id: application.education_level_id,
      education_form_id: application.education_form_id,
      program_id: application.program_id,
      notes: application.notes?.trim() || null,
    }
    if (admissionType.value === 'yangi_qabul') {
      payload.diplom_id = profile.value?.diplom?.id
    } else {
      payload.transfer_diplom_id = profile.value?.transfer_diplom?.id
      payload.course_id = transferDiplom.target_course_id
    }
    const created = await applicationsApi.submit(payload)
    toast.success("Ariza yuborildi")
    router.push(`/applicant/applications/${created.id}`)
  } catch (e) {
    handleApiError(e)
  } finally {
    submittingApp.value = false
  }
}

// ===========================================================================
// Shared
// ===========================================================================
function handleApiError(e: unknown) {
  const ax = e as AxiosError<{ error?: { message?: string; details?: any[] } }>
  const msg = ax.response?.data?.error?.message
  toast.error(msg || "Xatolik yuz berdi")

  // Map per-field details onto local errors map for inline highlight
  const details = ax.response?.data?.error?.details
  if (Array.isArray(details)) {
    const e: Record<string, string> = { ...errors.value }
    for (const d of details) {
      const path = (d.loc || []).filter((p: any) => typeof p === 'string' && p !== 'body')
      const field = path[path.length - 1]
      if (field && !e[field]) e[field] = d.msg || 'Xato'
    }
    errors.value = e
  }
}

async function loadInitial() {
  try {
    // Backend returns 200 + null for first-login users (no profile yet).
    profile.value = await applicantsApi.me()
  } catch {
    profile.value = null
  }
  if (profile.value) {
    Object.assign(personal, {
      last_name: profile.value.last_name || '',
      first_name: profile.value.first_name || '',
      other_name: profile.value.other_name || '',
      birth_date: profile.value.birth_date || '',
      gender: profile.value.gender || 'male',
      passport_series: profile.value.passport_series || '',
      pinfl: profile.value.pinfl || '',
      region_id: profile.value.region_id || null,
      district_id: profile.value.district_id || null,
      address: profile.value.address || '',
      nationality: profile.value.nationality || "O'zbek",
      additional_phone: profile.value.additional_phone || '',
      email: profile.value.email || '',
    })
    if (profile.value.diplom) {
      Object.assign(diplom, {
        serial_number: profile.value.diplom.serial_number,
        education_type_id: profile.value.diplom.education_type_id,
        institution_type_id: profile.value.diplom.institution_type_id,
        university_name: profile.value.diplom.university_name,
        graduation_year: profile.value.diplom.graduation_year,
        region_id: profile.value.diplom.region_id,
        district_id: profile.value.diplom.district_id,
        diploma_file_id: profile.value.diplom.diploma_file_id,
      })
      admissionType.value = 'yangi_qabul'
    } else if (profile.value.transfer_diplom) {
      Object.assign(transferDiplom, {
        country_id: profile.value.transfer_diplom.country_id,
        university_name: profile.value.transfer_diplom.university_name,
        target_course_id: profile.value.transfer_diplom.target_course_id,
        transcript_file_id: profile.value.transfer_diplom.transcript_file_id,
      })
      admissionType.value = 'perevod'
    }
  }
  try {
    const res = await applicationsApi.myList()
    myApplications.value = res
  } catch { /* ignore */ }
}

onMounted(async () => {
  initialLoading.value = true
  try {
    countries.value = await adminApi.countries.list().catch(() => [])
    const uz = countries.value.find(c => c.name === "O'zbekiston") || countries.value[0]
    if (uz) regions.value = await adminApi.regions.list(uz.id).catch(() => [])

    educationTypes.value = await adminApi.educationTypes.list().catch(() => [])
    institutionTypes.value = await adminApi.institutionTypes.list().catch(() => [])
    courses.value = await adminApi.courses.list().catch(() => [])
    branches.value = await adminApi.branches.list(false).catch(() => [])
    educationLevels.value = await adminApi.educationLevels.list().catch(() => [])
    educationForms.value = await adminApi.educationForms.list().catch(() => [])
    programs.value = await adminApi.programs.list().catch(() => []) as any[]

    await loadInitial()

    if (personal.region_id) {
      districts.value = await adminApi.districts.list(personal.region_id).catch(() => [])
    }
    if (diplom.region_id) {
      diplomDistricts.value = await adminApi.districts.list(diplom.region_id).catch(() => [])
    }

    // Auto-pick first step that's still incomplete.
    if (!stepStatus.value.profile) currentStep.value = 'profile'
    else if (!stepStatus.value.diplom) currentStep.value = 'diplom'
    else currentStep.value = 'application'

    // Default branch (single branch setup)
    if (branches.value.length === 1) application.branch_id = branches.value[0].id
  } finally {
    initialLoading.value = false
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Ro'yxatdan o'tish</h1>
      <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
        Ariza topshirish uchun 3 ta bosqichni ketma-ket bajaring.
      </p>
    </div>

    <!-- Stepper -->
    <div class="card p-4 sm:p-5">
      <ol class="flex items-start gap-3 sm:gap-4">
        <li v-for="(s, i) in stepDefs" :key="s.key"
            class="flex-1 min-w-0">
          <button
            class="w-full text-left group"
            :disabled="initialLoading"
            @click="gotoStep(s.key)"
          >
            <div class="flex items-center gap-2 sm:gap-3">
              <div
                class="grid place-items-center w-9 h-9 rounded-full text-sm font-semibold shrink-0 transition-colors"
                :class="stepStatus[s.key]
                  ? 'bg-emerald-500 text-white'
                  : currentStep === s.key
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400'"
              >
                <Check v-if="stepStatus[s.key]" class="w-4 h-4" />
                <component v-else :is="s.icon" class="w-4 h-4" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-xs font-semibold uppercase tracking-wide"
                     :class="currentStep === s.key
                       ? 'text-brand-600 dark:text-brand-300'
                       : 'text-slate-500 dark:text-slate-400'">
                  {{ i + 1 }}-qadam
                </div>
                <div class="text-sm font-medium truncate"
                     :class="stepStatus[s.key]
                       ? 'text-emerald-700 dark:text-emerald-400'
                       : 'text-slate-900 dark:text-slate-100'">
                  {{ s.title }}
                </div>
              </div>
            </div>
          </button>
          <div v-if="i < stepDefs.length - 1"
               class="hidden sm:block h-0.5 mt-4 ml-9 bg-slate-200 dark:bg-slate-700"></div>
        </li>
      </ol>
    </div>

    <div v-if="initialLoading" class="card p-10 text-center">
      <Loader2 class="w-6 h-6 mx-auto animate-spin text-slate-400" />
      <div class="mt-3 text-sm text-slate-500">Yuklanmoqda...</div>
    </div>

    <!-- ============================================================ -->
    <!-- Step 1: Profile + passport -->
    <!-- ============================================================ -->
    <section v-else-if="currentStep === 'profile'" class="card p-5 sm:p-6 space-y-5">
      <header class="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4">
        <UserIcon class="w-5 h-5 text-brand-600" />
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Shaxsiy ma'lumotlar va pasport</h2>
      </header>

      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="label">Familiya <span class="text-rose-500">*</span></label>
          <input v-model="personal.last_name" class="input uppercase"
                 :class="errors.last_name ? 'error' : ''" placeholder="Aliyev" />
          <p v-if="errors.last_name" class="field-error">{{ errors.last_name }}</p>
        </div>
        <div>
          <label class="label">Ism <span class="text-rose-500">*</span></label>
          <input v-model="personal.first_name" class="input uppercase"
                 :class="errors.first_name ? 'error' : ''" placeholder="Vali" />
          <p v-if="errors.first_name" class="field-error">{{ errors.first_name }}</p>
        </div>
        <div>
          <label class="label">Otasining ismi</label>
          <input v-model="personal.other_name" class="input uppercase" placeholder="Karimovich" />
        </div>
        <div>
          <label class="label">Tug'ilgan sana <span class="text-rose-500">*</span></label>
          <input v-model="personal.birth_date" type="date" class="input"
                 :class="errors.birth_date ? 'error' : ''" />
          <p v-if="errors.birth_date" class="field-error">{{ errors.birth_date }}</p>
        </div>
        <div>
          <label class="label">Jinsi <span class="text-rose-500">*</span></label>
          <select v-model="personal.gender" class="input">
            <option value="male">Erkak</option>
            <option value="female">Ayol</option>
          </select>
        </div>
        <div>
          <label class="label">Millati</label>
          <input v-model="personal.nationality" class="input" />
        </div>
        <div>
          <label class="label inline-flex items-center gap-1.5">
            <IdCard class="w-3 h-3" /> Pasport seriyasi va raqami <span class="text-rose-500">*</span>
          </label>
          <input v-model="personal.passport_series" class="input uppercase font-mono"
                 maxlength="9" placeholder="AA1234567"
                 :class="errors.passport_series ? 'error' : ''" />
          <p v-if="errors.passport_series" class="field-error">{{ errors.passport_series }}</p>
          <p v-else class="field-hint">2 harf + 7 raqam (jami 9 belgi)</p>
        </div>
        <div>
          <label class="label">JSHSHIR (PINFL) <span class="text-rose-500">*</span></label>
          <input v-model="personal.pinfl" class="input font-mono"
                 maxlength="14" placeholder="12345678901234"
                 :class="errors.pinfl ? 'error' : ''" />
          <p v-if="errors.pinfl" class="field-error">{{ errors.pinfl }}</p>
          <p v-else class="field-hint">14 ta raqam</p>
        </div>
        <div>
          <label class="label">Qo'shimcha telefon</label>
          <input v-model="personal.additional_phone" class="input" placeholder="+998 90 123 45 67"
                 :class="errors.additional_phone ? 'error' : ''" />
          <p v-if="errors.additional_phone" class="field-error">{{ errors.additional_phone }}</p>
        </div>
        <div>
          <label class="label">Email</label>
          <input v-model="personal.email" type="email" class="input" placeholder="vali@example.com"
                 :class="errors.email ? 'error' : ''" />
          <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
        </div>
        <div>
          <label class="label">Viloyat</label>
          <select v-model="personal.region_id" class="input">
            <option :value="null">— tanlang —</option>
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Tuman</label>
          <select v-model="personal.district_id" class="input" :disabled="!personal.region_id">
            <option :value="null">— tanlang —</option>
            <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <div class="sm:col-span-2">
          <label class="label">Yashash manzili</label>
          <input v-model="personal.address" class="input" placeholder="Ko'cha, uy, kvartira" />
        </div>
      </div>

      <div class="flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800">
        <button class="btn-primary" :disabled="savingProfile" @click="saveProfile">
          <Loader2 v-if="savingProfile" class="w-4 h-4 animate-spin" />
          <Save v-else class="w-4 h-4" />
          {{ savingProfile ? 'Saqlanmoqda...' : "Saqlash va davom etish" }}
          <ArrowRight v-if="!savingProfile" class="w-4 h-4" />
        </button>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- Step 2: Diplom / Attestat -->
    <!-- ============================================================ -->
    <section v-else-if="currentStep === 'diplom'" class="card p-5 sm:p-6 space-y-5">
      <header class="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4">
        <GraduationCap class="w-5 h-5 text-brand-600" />
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Diplom yoki attestat</h2>
      </header>

      <!-- Admission type selector -->
      <div>
        <label class="label">Qabul turini tanlang <span class="text-rose-500">*</span></label>
        <div class="grid sm:grid-cols-2 gap-3">
          <button
            type="button"
            class="card-button p-4 text-left transition-all"
            :class="admissionType === 'yangi_qabul'
              ? 'border-brand-500 ring-2 ring-brand-500/20 bg-brand-50/40 dark:bg-brand-500/10'
              : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'"
            @click="admissionType = 'yangi_qabul'"
          >
            <div class="font-semibold text-slate-900 dark:text-slate-100">1-kursga qabul</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Maktab yoki kollej attestati / diplomi bilan
            </div>
          </button>
          <button
            type="button"
            class="card-button p-4 text-left transition-all"
            :class="admissionType === 'perevod'
              ? 'border-brand-500 ring-2 ring-brand-500/20 bg-brand-50/40 dark:bg-brand-500/10'
              : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'"
            @click="admissionType = 'perevod'"
          >
            <div class="font-semibold text-slate-900 dark:text-slate-100">O'qishni ko'chirish</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Boshqa universitetdan perevod
            </div>
          </button>
        </div>
      </div>

      <!-- 1-kurs form -->
      <div v-if="admissionType === 'yangi_qabul'" class="grid sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100 dark:border-slate-800">
        <div>
          <label class="label">Diplom yoki shahodatnoma seriyasi <span class="text-rose-500">*</span></label>
          <input v-model="diplom.serial_number" class="input font-mono"
                 :class="errors.diplom_series ? 'error' : ''"
                 placeholder="A-1234567" />
          <p v-if="errors.diplom_series" class="field-error">{{ errors.diplom_series }}</p>
        </div>
        <div>
          <label class="label">Hujjat turi <span class="text-rose-500">*</span></label>
          <select v-model="diplom.education_type_id" class="input"
                  :class="errors.education_type_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="t in educationTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <p v-if="errors.education_type_id" class="field-error">{{ errors.education_type_id }}</p>
        </div>
        <div>
          <label class="label">Muassasa turi <span class="text-rose-500">*</span></label>
          <select v-model="diplom.institution_type_id" class="input"
                  :class="errors.institution_type_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="t in institutionTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <p v-if="errors.institution_type_id" class="field-error">{{ errors.institution_type_id }}</p>
        </div>
        <div>
          <label class="label">Bitirgan yili <span class="text-rose-500">*</span></label>
          <input v-model="diplom.graduation_year" type="text" class="input font-mono"
                 maxlength="4" placeholder="2024"
                 :class="errors.graduation_year ? 'error' : ''" />
          <p v-if="errors.graduation_year" class="field-error">{{ errors.graduation_year }}</p>
        </div>
        <div class="sm:col-span-2">
          <label class="label">Muassasa nomi <span class="text-rose-500">*</span></label>
          <input v-model="diplom.university_name" class="input"
                 :class="errors.university_name ? 'error' : ''"
                 placeholder="Toshkent davlat universiteti" />
          <p v-if="errors.university_name" class="field-error">{{ errors.university_name }}</p>
        </div>
        <div>
          <label class="label">Viloyat <span class="text-rose-500">*</span></label>
          <select v-model="diplom.region_id" class="input"
                  :class="errors.region_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
          <p v-if="errors.region_id" class="field-error">{{ errors.region_id }}</p>
        </div>
        <div>
          <label class="label">Tuman <span class="text-rose-500">*</span></label>
          <select v-model="diplom.district_id" class="input"
                  :disabled="!diplom.region_id"
                  :class="errors.district_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="d in diplomDistricts" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
          <p v-if="errors.district_id" class="field-error">{{ errors.district_id }}</p>
        </div>
        <div class="sm:col-span-2">
          <label class="label">Diplom yoki shahodatnoma <span class="text-rose-500">*</span></label>
          <FileUpload v-model="diplom.diploma_file_id" subdir="diploms"
                      hint="PDF yoki rasm. Fayl o'lchami eng ko'pi 10 MB." />
          <p v-if="errors.diploma_file_id" class="field-error">{{ errors.diploma_file_id }}</p>
        </div>
      </div>

      <!-- Perevod form -->
      <div v-else class="grid sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100 dark:border-slate-800">
        <div>
          <label class="label">Davlat <span class="text-rose-500">*</span></label>
          <select v-model="transferDiplom.country_id" class="input"
                  :class="errors.country_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="c in countries" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <p v-if="errors.country_id" class="field-error">{{ errors.country_id }}</p>
        </div>
        <div>
          <label class="label">Kurs <span class="text-rose-500">*</span></label>
          <select v-model="transferDiplom.target_course_id" class="input"
                  :class="errors.target_course_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <p v-if="errors.target_course_id" class="field-error">{{ errors.target_course_id }}</p>
        </div>
        <div class="sm:col-span-2">
          <label class="label">Muassasa nomi <span class="text-rose-500">*</span></label>
          <input v-model="transferDiplom.university_name" class="input"
                 :class="errors.university_name ? 'error' : ''"
                 placeholder="Moskva davlat universiteti" />
          <p v-if="errors.university_name" class="field-error">{{ errors.university_name }}</p>
        </div>
        <div class="sm:col-span-2">
          <label class="label">Transkript fayli <span class="text-rose-500">*</span></label>
          <FileUpload v-model="transferDiplom.transcript_file_id" subdir="transfer-diploms"
                      hint="Akademik transkript (PDF). Fayl o'lchami eng ko'pi 10 MB." />
          <p v-if="errors.transcript_file_id" class="field-error">{{ errors.transcript_file_id }}</p>
        </div>
      </div>

      <div class="flex justify-between pt-4 border-t border-slate-100 dark:border-slate-800">
        <button class="btn-secondary" @click="gotoStep('profile')">
          <ArrowLeft class="w-4 h-4" />
          Orqaga
        </button>
        <button class="btn-primary" :disabled="savingDiplom" @click="saveDiplom">
          <Loader2 v-if="savingDiplom" class="w-4 h-4 animate-spin" />
          <Save v-else class="w-4 h-4" />
          {{ savingDiplom ? 'Saqlanmoqda...' : "Saqlash va davom etish" }}
          <ArrowRight v-if="!savingDiplom" class="w-4 h-4" />
        </button>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- Step 3: Application -->
    <!-- ============================================================ -->
    <section v-else-if="currentStep === 'application'" class="card p-5 sm:p-6 space-y-5">
      <header class="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4">
        <ClipboardList class="w-5 h-5 text-brand-600" />
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Yo'nalishga ariza</h2>
      </header>

      <div v-if="myApplications.length"
           class="rounded-lg p-4 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200/60 dark:border-emerald-700/30 flex items-start gap-3">
        <CheckCircle2 class="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
        <div>
          <div class="text-sm font-semibold text-emerald-900 dark:text-emerald-200">
            Sizning {{ myApplications.length }} ta arizangiz mavjud
          </div>
          <p class="text-xs mt-1 text-emerald-800 dark:text-emerald-300">
            Quyidan yana bir ariza topshirishingiz mumkin yoki
            <router-link to="/applicant/applications" class="underline font-medium">arizalarim</router-link>
            bo'limiga o'ting.
          </p>
        </div>
      </div>

      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="label">Filial <span class="text-rose-500">*</span></label>
          <select v-model="application.branch_id" class="input"
                  :class="errors.branch_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
          <p v-if="errors.branch_id" class="field-error">{{ errors.branch_id }}</p>
        </div>
        <div>
          <label class="label">Ta'lim darajasi <span class="text-rose-500">*</span></label>
          <select v-model="application.education_level_id" class="input"
                  :class="errors.education_level_id ? 'error' : ''">
            <option value="">— tanlang —</option>
            <option v-for="l in educationLevels" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
          <p v-if="errors.education_level_id" class="field-error">{{ errors.education_level_id }}</p>
        </div>
        <div>
          <label class="label">Ta'lim shakli <span class="text-rose-500">*</span></label>
          <select v-model="application.education_form_id" class="input"
                  :class="errors.education_form_id ? 'error' : ''"
                  :disabled="filteredForms.length <= 1 && admissionType === 'yangi_qabul'">
            <option value="">— tanlang —</option>
            <option v-for="f in filteredForms" :key="f.id" :value="f.id">{{ f.name }}</option>
          </select>
          <p v-if="errors.education_form_id" class="field-error">{{ errors.education_form_id }}</p>
          <p v-if="admissionType === 'yangi_qabul'" class="field-hint">
            1-kursga topshirish faqat Kunduzgi shaklda mumkin.
          </p>
        </div>
        <div>
          <label class="label">Yo'nalish <span class="text-rose-500">*</span></label>
          <select v-model="application.program_id" class="input"
                  :class="errors.program_id ? 'error' : ''"
                  :disabled="!filteredPrograms.length">
            <option value="">— tanlang —</option>
            <option v-for="p in filteredPrograms" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
          <p v-if="errors.program_id" class="field-error">{{ errors.program_id }}</p>
          <p v-if="!filteredPrograms.length && application.education_level_id"
             class="field-hint text-amber-600">
            Ushbu shartlarga mos yo'nalish topilmadi
          </p>
        </div>
        <div class="sm:col-span-2">
          <label class="label">Qo'shimcha izoh</label>
          <textarea v-model="application.notes" class="input" rows="3"
                    placeholder="Operatorlar uchun qoldirmoqchi bo'lgan ma'lumot (ixtiyoriy)" />
        </div>
      </div>

      <div class="flex justify-between pt-4 border-t border-slate-100 dark:border-slate-800">
        <button class="btn-secondary" @click="gotoStep('diplom')">
          <ArrowLeft class="w-4 h-4" />
          Orqaga
        </button>
        <button class="btn-primary" :disabled="submittingApp" @click="submitApplication">
          <Loader2 v-if="submittingApp" class="w-4 h-4 animate-spin" />
          <ClipboardList v-else class="w-4 h-4" />
          {{ submittingApp ? 'Yuborilmoqda...' : "Arizani yuborish" }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.label {
  @apply block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1;
}
.field-error {
  @apply mt-1 text-xs text-rose-600 dark:text-rose-400 inline-flex items-center gap-1;
}
.field-hint {
  @apply mt-1 text-[11px] text-slate-500 dark:text-slate-400;
}
.input.error {
  @apply border-rose-500 focus:ring-rose-500/30;
}
.btn-secondary {
  @apply inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800;
}
.card-button {
  @apply rounded-xl border-2 cursor-pointer;
}
</style>
