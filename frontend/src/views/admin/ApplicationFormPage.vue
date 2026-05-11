<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Save, UserPlus, Search, X, Award, Check } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import {
  adminApi,
  type BranchRead,
  type CountryRead,
  type DistrictRead,
  type NamedRecord,
  type ProgramRead,
  type RegionRead,
} from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import FileUpload from '@/components/ui/FileUpload.vue'
import {
  PLACEHOLDERS,
  formatNameUpper,
  formatPassport,
  formatPhone,
  compactPhone,
  formatPinfl,
  formatYear,
  passport as vPassport,
  phoneUz as vPhone,
  pinfl as vPinfl,
  year as vYear,
} from '@/utils/validators'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const id = computed(() => route.params.id as string | undefined)
const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')
// If we're converting a Lead, this holds its UUID so we can attach it on submit.
const leadId = ref<string | null>(null)
const isEdit = computed(() => !!id.value)

// =============================================================================
// Application form state
// =============================================================================
const form = reactive({
  applicant_id: '',
  applicant_user_id: '',
  admission_type: 'yangi_qabul' as 'yangi_qabul' | 'perevod',
  branch_id: '',
  education_level_id: '',
  education_form_id: '',
  program_id: '',
  diplom_id: '' as string | '',
  transfer_diplom_id: '' as string | '',
  course_id: '' as string | '',
  notes: '',
})

const errors = ref<Record<string, string>>({})
const saving = ref(false)
const loading = ref(false)

// =============================================================================
// STEP 1 — Applicant search + inline create
// =============================================================================
const applicantSearch = ref('')
const applicantResults = ref<any[]>([])
const selectedApplicantLabel = ref('')
const showInlineCreate = ref(false)
const creatingApplicant = ref(false)
// In edit mode the operator can toggle this on to expose the same applicant
// fields inline and save personal-info changes alongside the application update.
const applicantEditOpen = ref(false)
const applicantSaving = ref(false)

const inlineApplicant = reactive({
  phone: '+998',
  additional_phone: '',
  telegram_username: '',
  last_name: '',
  first_name: '',
  other_name: '',
  birth_date: '',
  gender: 'male' as 'male' | 'female',
  passport_series: '',
  pinfl: '',
  region_id: '' as string,
  district_id: '' as string,
  address: '',
  nationality: "O'zbek",
})
const inlineErrors = ref<Record<string, string>>({})
const inlineDistricts = ref<DistrictRead[]>([])

watch(() => inlineApplicant.region_id, async (rid) => {
  if (prefilling.value) return  // preserve district_id while we hydrate
  inlineApplicant.district_id = ''
  inlineDistricts.value = rid ? await adminApi.districts.list(rid) : []
})

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(applicantSearch, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q || q.length < 2) {
    applicantResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const res = await adminApi.applicants.list({ search: q, page: 1, size: 10 })
      applicantResults.value = res.items
    } catch {
      applicantResults.value = []
    }
  }, 300)
})

async function selectApplicant(a: any) {
  form.applicant_id = a.id
  form.applicant_user_id = a.user_id
  selectedApplicantLabel.value = formatApplicant(a)
  applicantSearch.value = ''
  applicantResults.value = []
  showInlineCreate.value = false
  await loadDiplomsForUser(a.user_id)
}

function clearApplicant() {
  form.applicant_id = ''
  form.applicant_user_id = ''
  selectedApplicantLabel.value = ''
  myDiplom.value = null
  myTransferDiplom.value = null
  form.diplom_id = ''
  form.transfer_diplom_id = ''
}

function formatApplicant(a: any) {
  const fio = [a.last_name, a.first_name, a.other_name].filter(Boolean).join(' ')
  return fio || `Abituriyent ${a.id.slice(0, 8)}`
}

function openInlineCreate() {
  showInlineCreate.value = true
  if (/^\+?\d/.test(applicantSearch.value)) {
    inlineApplicant.phone = applicantSearch.value.startsWith('+')
      ? applicantSearch.value
      : '+998' + applicantSearch.value
  }
  applicantResults.value = []
  inlineErrors.value = {}
  nextTick(() => document.getElementById('inline-applicant-phone')?.focus())
}

function validateInlineField(field: string) {
  const ne = { ...inlineErrors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'phone':           err = vPhone(inlineApplicant.phone); break
    case 'last_name':       err = inlineApplicant.last_name.trim() ? null : 'Familiya majburiy'; break
    case 'first_name':      err = inlineApplicant.first_name.trim() ? null : 'Ism majburiy'; break
    case 'birth_date':      err = inlineApplicant.birth_date ? null : "Tug'ilgan sana majburiy"; break
    case 'passport_series': err = vPassport(inlineApplicant.passport_series); break
    case 'pinfl':           err = vPinfl(inlineApplicant.pinfl); break
  }
  if (err) ne[field] = err
  inlineErrors.value = ne
}

function onInlinePhone(e: Event)    { inlineApplicant.phone = formatPhone((e.target as HTMLInputElement).value); validateInlineField('phone') }
function onInlineAddPhone(e: Event) { inlineApplicant.additional_phone = formatPhone((e.target as HTMLInputElement).value) }
function onInlineLast(e: Event)     { inlineApplicant.last_name = formatNameUpper((e.target as HTMLInputElement).value); validateInlineField('last_name') }
function onInlineFirst(e: Event)    { inlineApplicant.first_name = formatNameUpper((e.target as HTMLInputElement).value); validateInlineField('first_name') }
function onInlineOther(e: Event)    { inlineApplicant.other_name = formatNameUpper((e.target as HTMLInputElement).value) }
function onInlinePassport(e: Event) { inlineApplicant.passport_series = formatPassport((e.target as HTMLInputElement).value); validateInlineField('passport_series') }
function onInlinePinfl(e: Event)    { inlineApplicant.pinfl = formatPinfl((e.target as HTMLInputElement).value); validateInlineField('pinfl') }

async function createApplicantInline() {
  ;['phone', 'last_name', 'first_name', 'birth_date', 'passport_series', 'pinfl'].forEach(validateInlineField)
  if (Object.keys(inlineErrors.value).length) {
    toast.error("Maydonlarni to'g'ri to'ldiring")
    return
  }
  creatingApplicant.value = true
  try {
    const payload = {
      ...inlineApplicant,
      phone: compactPhone(inlineApplicant.phone),
      additional_phone: inlineApplicant.additional_phone ? compactPhone(inlineApplicant.additional_phone) : null,
      telegram_username: inlineApplicant.telegram_username ? inlineApplicant.telegram_username.trim().replace(/^@/, '') : null,
      address: inlineApplicant.address.trim() || null,
      passport_series: inlineApplicant.passport_series ? inlineApplicant.passport_series.toUpperCase() : null,
      pinfl: inlineApplicant.pinfl || null,
      other_name: inlineApplicant.other_name || null,
      region_id: inlineApplicant.region_id || null,
      district_id: inlineApplicant.district_id || null,
    }
    const created = await adminApi.applicants.create(payload)
    toast.success("Abituriyent yaratildi")
    showInlineCreate.value = false
    await selectApplicant(created)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yaratib bo'lmadi")
  } finally {
    creatingApplicant.value = false
  }
}

// =============================================================================
// STEP 2.5 — Diplom (yangi_qabul) or transfer diplom (perevod) inline create
// =============================================================================
const myDiplom = ref<any | null>(null)
const myTransferDiplom = ref<any | null>(null)

async function loadDiplomsForUser(user_id: string) {
  myDiplom.value = null
  myTransferDiplom.value = null
  try {
    const [d, t] = await Promise.all([
      adminApi.diploms.list({ user_id }).catch(() => ({ items: [] }) as any),
      adminApi.transferDiploms.list({ user_id }).catch(() => ({ items: [] }) as any),
    ])
    myDiplom.value = (d as any).items?.[0] || null
    myTransferDiplom.value = (t as any).items?.[0] || null
    if (myDiplom.value) form.diplom_id = myDiplom.value.id
    if (myTransferDiplom.value) form.transfer_diplom_id = myTransferDiplom.value.id
  } catch {
    /* ignore */
  }
}

const showDiplomForm = ref(false)
const showTransferForm = ref(false)

const diplomForm = reactive({
  serial_number: '',
  education_type_id: '',
  institution_type_id: '',
  university_name: '',
  graduation_year: '',
  region_id: '',
  district_id: '',
  diploma_file_id: null as string | null,
})
const diplomErrors = ref<Record<string, string>>({})
const diplomDistricts = ref<DistrictRead[]>([])
const diplomCreating = ref(false)

watch(() => diplomForm.region_id, async (rid) => {
  diplomForm.district_id = ''
  diplomDistricts.value = rid ? await adminApi.districts.list(rid) : []
})

function onGradYear(e: Event) {
  diplomForm.graduation_year = formatYear((e.target as HTMLInputElement).value)
  validateDiplomField('graduation_year')
}

function validateDiplomField(field: string) {
  const ne = { ...diplomErrors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'serial_number':       err = diplomForm.serial_number.trim() ? null : 'Diplom raqamini kiriting'; break
    case 'education_type_id':   err = diplomForm.education_type_id ? null : "Ta'lim turini tanlang"; break
    case 'institution_type_id': err = diplomForm.institution_type_id ? null : 'Muassasa turini tanlang'; break
    case 'university_name':     err = diplomForm.university_name.trim() ? null : 'Universitet nomini kiriting'; break
    case 'graduation_year':     err = vYear(diplomForm.graduation_year); break
    case 'region_id':           err = diplomForm.region_id ? null : "Viloyatni tanlang"; break
    case 'district_id':         err = diplomForm.district_id ? null : "Tumanni tanlang"; break
  }
  if (err) ne[field] = err
  diplomErrors.value = ne
}

async function createDiplomInline() {
  ;['serial_number', 'education_type_id', 'institution_type_id', 'university_name',
    'graduation_year', 'region_id', 'district_id'].forEach(validateDiplomField)
  if (Object.keys(diplomErrors.value).length) {
    toast.error("Diplom maydonlarini to'ldiring")
    return
  }
  diplomCreating.value = true
  try {
    const payload = { user_id: form.applicant_user_id, ...diplomForm }
    const created = await adminApi.diploms.create(payload)
    toast.success("Diplom qo'shildi")
    showDiplomForm.value = false
    myDiplom.value = created
    form.diplom_id = created.id
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    diplomCreating.value = false
  }
}

const transferForm = reactive({
  country_id: '',
  university_name: '',
  target_course_id: '',
  transcript_file_id: null as string | null,
})
const transferErrors = ref<Record<string, string>>({})
const transferCreating = ref(false)

function validateTransferField(field: string) {
  const ne = { ...transferErrors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'country_id':       err = transferForm.country_id ? null : "Davlatni tanlang"; break
    case 'university_name':  err = transferForm.university_name.trim() ? null : 'Universitet nomini kiriting'; break
    case 'target_course_id': err = transferForm.target_course_id ? null : "Maqsadli kursni tanlang"; break
  }
  if (err) ne[field] = err
  transferErrors.value = ne
}

async function createTransferInline() {
  ;['country_id', 'university_name', 'target_course_id'].forEach(validateTransferField)
  if (Object.keys(transferErrors.value).length) {
    toast.error("Maydonlarni to'ldiring")
    return
  }
  transferCreating.value = true
  try {
    const payload = { user_id: form.applicant_user_id, ...transferForm }
    const created = await adminApi.transferDiploms.create(payload)
    toast.success("Perevod diplomi qo'shildi")
    showTransferForm.value = false
    myTransferDiplom.value = created
    form.transfer_diplom_id = created.id
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    transferCreating.value = false
  }
}

// =============================================================================
// STEP 3 — Cascading branch → level → form → program
// =============================================================================
const branches = ref<BranchRead[]>([])
const allEducationLevels = ref<NamedRecord[]>([])
const allEducationForms = ref<NamedRecord[]>([])
const allPrograms = ref<ProgramRead[]>([])
const courses = ref<NamedRecord[]>([])
const educationTypes = ref<NamedRecord[]>([])
const institutionTypes = ref<NamedRecord[]>([])
const countries = ref<CountryRead[]>([])
const regions = ref<RegionRead[]>([])

const availableLevels = computed(() => {
  if (!form.branch_id) return []
  const ids = new Set(allPrograms.value.filter((p) => p.branch_id === form.branch_id).map((p) => p.education_level_id))
  return allEducationLevels.value.filter((l) => ids.has(l.id))
})
const availableForms = computed(() => {
  if (!form.branch_id || !form.education_level_id) return []
  const ids = new Set(
    allPrograms.value
      .filter((p) => p.branch_id === form.branch_id && p.education_level_id === form.education_level_id)
      .map((p) => p.education_form_id),
  )
  let forms = allEducationForms.value.filter((f) => ids.has(f.id))
  // Business rule: 1-kurs (yangi_qabul) applicants can only enroll in
  // kunduzgi. Mirrors the limit applicants see in the onboarding wizard.
  if (form.admission_type === 'yangi_qabul') {
    forms = forms.filter((f: any) =>
      (f.name || '').toLowerCase().includes('kunduz')
    )
  }
  return forms
})
const availablePrograms = computed(() => {
  if (!form.branch_id || !form.education_level_id || !form.education_form_id) return []
  return allPrograms.value.filter(
    (p) =>
      p.branch_id === form.branch_id &&
      p.education_level_id === form.education_level_id &&
      p.education_form_id === form.education_form_id,
  )
})

const prefilling = ref(false)
watch(() => form.branch_id, () => {
  if (prefilling.value) return
  form.education_level_id = ''; form.education_form_id = ''; form.program_id = ''
})
watch(() => form.education_level_id, () => {
  if (prefilling.value) return
  form.education_form_id = ''; form.program_id = ''
})
watch(() => form.education_form_id, () => {
  if (prefilling.value) return
  form.program_id = ''
})

// Switching admission_type re-applies the kunduzgi-only rule.
// If the selected form is no longer in availableForms (e.g. user picked
// Sirtqi then switched to 1-kurs), drop it so they re-pick.
watch(() => form.admission_type, () => {
  if (prefilling.value) return
  if (form.education_form_id && !availableForms.value.find((f: any) => f.id === form.education_form_id)) {
    form.education_form_id = ''
    form.program_id = ''
  }
})

const selectedProgram = computed(() => allPrograms.value.find((p) => p.id === form.program_id))

const levelPlaceholder = computed(() => {
  if (!form.branch_id) return "Avval filialni tanlang"
  return availableLevels.value.length ? "— darajani tanlang —" : "Bu filialda yo'nalishlar yo'q"
})
const formPlaceholder = computed(() => {
  if (!form.education_level_id) return "Avval darajani tanlang"
  return availableForms.value.length ? "— shaklni tanlang —" : "Bu kombinatsiyada shakl yo'q"
})
const programPlaceholder = computed(() => {
  if (!form.education_form_id) return "Avval shaklni tanlang"
  return availablePrograms.value.length ? "— yo'nalishni tanlang —" : "Bu kombinatsiyada yo'nalish yo'q"
})

// =============================================================================
// Init
// =============================================================================
onMounted(async () => {
  loading.value = true
  try {
    ;[
      branches.value,
      allEducationLevels.value,
      allEducationForms.value,
      allPrograms.value,
      courses.value,
      educationTypes.value,
      institutionTypes.value,
      countries.value,
    ] = await Promise.all([
      adminApi.branches.list(false),
      adminApi.educationLevels.list(),
      adminApi.educationForms.list(),
      // Load ALL programs (including inactive) so an edit mode on an
      // application created against a now-deactivated program can still
      // resolve the dropdowns — otherwise the form/program selects fall
      // back to placeholder even though the row clearly has values.
      adminApi.programs.list({ active_only: false }),
      adminApi.courses.list(),
      adminApi.educationTypes.list(),
      adminApi.institutionTypes.list(),
      adminApi.countries.list(),
    ])
    const uz = countries.value.find((c) => c.name === "O'zbekiston") || countries.value[0]
    if (uz) regions.value = await adminApi.regions.list(uz.id)

    if (isEdit.value && id.value) {
      const a = await adminApi.applications.get(id.value)
      prefilling.value = true
      Object.assign(form, {
        applicant_id: a.applicant_id,
        admission_type: a.admission_type,
        branch_id: a.branch_id,
        education_level_id: a.education_level_id,
        education_form_id: a.education_form_id,
        program_id: a.program_id,
        diplom_id: a.diplom_id || '',
        transfer_diplom_id: a.transfer_diplom_id || '',
        course_id: a.course_id || '',
        notes: a.notes || '',
      })
      const ap = await adminApi.applicants.get(a.applicant_id)
      form.applicant_user_id = ap.user_id
      selectedApplicantLabel.value = formatApplicant(ap)
      // Populate the inline applicant form so the operator can edit personal
      // info from this same page without navigating away.
      Object.assign(inlineApplicant, {
        phone: '+998',
        additional_phone: ap.additional_phone ? formatPhone(ap.additional_phone) : '',
        telegram_username: ap.telegram_username || '',
        last_name: ap.last_name || '',
        first_name: ap.first_name || '',
        other_name: ap.other_name || '',
        birth_date: ap.birth_date || '',
        gender: ap.gender || 'male',
        passport_series: ap.passport_series || '',
        pinfl: ap.pinfl || '',
        region_id: ap.region_id || '',
        district_id: ap.district_id || '',
        address: ap.address || '',
        nationality: ap.nationality || "O'zbek",
      })
      if (ap.region_id) {
        inlineDistricts.value = await adminApi.districts.list(ap.region_id).catch(() => [])
      }
      await loadDiplomsForUser(ap.user_id)
      // Release the prefill gate after Vue's reactive watchers have flushed.
      await nextTick()
      prefilling.value = false
    }

    // === Lead → Application convert flow ===
    // If the URL has ?lead_id=..., we're converting that lead. Prefill the form's
    // funnel-aware fields (branch/program/notes) and remember the lead_id to send
    // back on submit.
    const leadIdParam = route.query.lead_id as string | undefined
    if (!isEdit.value && leadIdParam) {
      try {
        const { leadsApi } = await import('@/api/leads.api')
        const prefill = await leadsApi.prefill(leadIdParam)
        prefilling.value = true
        leadId.value = prefill.lead_id
        if (prefill.branch_id) form.branch_id = prefill.branch_id
        if (prefill.program_id) form.program_id = prefill.program_id
        if (prefill.notes) form.notes = prefill.notes

        // Try to find an existing applicant by the lead's phone first.
        // If found → auto-select. Otherwise → auto-open the inline "new applicant" form
        // prefilled with the lead's data so the operator just fills missing fields.
        let existing: any = null
        if (prefill.phone) {
          try {
            const r = await adminApi.applicants.list({ search: prefill.phone, page: 1, size: 1 })
            existing = (r.items as any[])[0] || null
          } catch { /* ignore */ }
        }
        if (existing) {
          form.applicant_id = existing.id
          form.applicant_user_id = existing.user_id
          selectedApplicantLabel.value = formatApplicant(existing)
          await loadDiplomsForUser(existing.user_id)
          toast.success("Abituriyent topildi: " + selectedApplicantLabel.value)
        } else {
          // No match — open inline form prefilled with lead data
          showInlineCreate.value = true
          inlineApplicant.phone = prefill.phone ? formatPhone(prefill.phone) : '+998'
          inlineApplicant.last_name = formatNameUpper(prefill.last_name || '')
          inlineApplicant.first_name = formatNameUpper(prefill.first_name || '')
          inlineApplicant.other_name = formatNameUpper(prefill.other_name || '')
          // Lead's telegram_username (if any) — also carried via prefill
          if ((prefill as any).telegram_username) {
            inlineApplicant.telegram_username = (prefill as any).telegram_username
          }
          // Track the search input too so the UI shows what we used
          applicantSearch.value = prefill.phone || `${prefill.last_name} ${prefill.first_name}`.trim()
          toast.success("Lead ma'lumotlari yuklandi — abituriyent ma'lumotlarini to'ldiring")
        }

        await nextTick()
        prefilling.value = false
      } catch {
        toast.error("Lead'ni yuklab bo'lmadi")
      }
    }
  } finally {
    loading.value = false
  }
})

function validate(): boolean {
  const e: Record<string, string> = {}
  if (!form.applicant_id) e.applicant_id = "Abituriyentni tanlang yoki yarating"
  if (!form.branch_id) e.branch_id = "Filialni tanlang"
  if (!form.education_level_id) e.education_level_id = "Ta'lim darajasini tanlang"
  if (!form.education_form_id) e.education_form_id = "Ta'lim shaklini tanlang"
  if (!form.program_id) e.program_id = "Yo'nalishni tanlang"
  if (form.admission_type === 'yangi_qabul' && !form.diplom_id) {
    e.diplom_id = "1-kurs uchun diplom kerak — yuqorida qo'shing"
  }
  if (form.admission_type === 'perevod') {
    if (!form.transfer_diplom_id) e.transfer_diplom_id = "Perevod diplomi kerak — yuqorida qo'shing"
    if (!form.course_id) e.course_id = "Maqsadli kursni tanlang"
  }
  errors.value = e
  return Object.keys(e).length === 0
}

async function submit() {
  if (!validate()) {
    toast.error("Maydonlarni to'ldiring")
    return
  }
  saving.value = true
  try {
    const payload: any = {
      applicant_id: form.applicant_id,
      admission_type: form.admission_type,
      branch_id: form.branch_id,
      education_level_id: form.education_level_id,
      education_form_id: form.education_form_id,
      program_id: form.program_id,
      notes: form.notes || null,
    }
    if (form.admission_type === 'yangi_qabul') {
      payload.diplom_id = form.diplom_id || null
      // Clear any stale perevod FKs so switching types from edit mode
      // doesn't leave orphaned references on the row.
      payload.transfer_diplom_id = null
      payload.course_id = null
    } else {
      payload.transfer_diplom_id = form.transfer_diplom_id || null
      payload.course_id = form.course_id || null
      payload.diplom_id = null
    }

    if (isEdit.value && id.value) {
      delete payload.applicant_id
      // admission_type IS now editable in edit mode — keep it on the payload so
      // the backend can switch a yangi_qabul ariza to perevod or vice versa.
      // If the operator opened the inline applicant editor, validate and persist
      // those changes against the applicant record before updating the application.
      if (applicantEditOpen.value && form.applicant_id) {
        ;['last_name', 'first_name', 'birth_date', 'passport_series', 'pinfl'].forEach(validateInlineField)
        if (Object.keys(inlineErrors.value).length) {
          toast.error("Abituriyent ma'lumotlarini to'g'ri to'ldiring")
          saving.value = false
          return
        }
        applicantSaving.value = true
        try {
          await adminApi.applicants.update(form.applicant_id, {
            last_name: inlineApplicant.last_name,
            first_name: inlineApplicant.first_name,
            other_name: inlineApplicant.other_name || null,
            birth_date: inlineApplicant.birth_date,
            gender: inlineApplicant.gender,
            passport_series: inlineApplicant.passport_series ? inlineApplicant.passport_series.toUpperCase() : null,
            pinfl: inlineApplicant.pinfl || null,
            additional_phone: inlineApplicant.additional_phone ? compactPhone(inlineApplicant.additional_phone) : null,
            telegram_username: inlineApplicant.telegram_username
              ? inlineApplicant.telegram_username.trim().replace(/^@/, '')
              : null,
            region_id: inlineApplicant.region_id || null,
            district_id: inlineApplicant.district_id || null,
            address: inlineApplicant.address.trim() || null,
            nationality: inlineApplicant.nationality || "O'zbek",
          })
        } finally {
          applicantSaving.value = false
        }
      }
      await adminApi.applications.update(id.value, payload)
      toast.success("Saqlandi")
    } else {
      // If we're converting a Lead, include lead_id so the backend marks it as won.
      if (leadId.value) payload.lead_id = leadId.value
      await adminApi.applications.create(payload)
      toast.success(leadId.value ? "Ariza yaratildi va lead arizaga aylantirildi" : "Ariza yaratildi")
    }
    router.push(`${panelPrefix.value}/applications`)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <PageHeader
      :title="isEdit ? 'Arizani tahrirlash' : 'Yangi ariza'"
      subtitle="Hammasi shu yerdan: abituriyent · diplom · qabul turi · yo'nalish"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'Arizalar', to: `${panelPrefix}/applications` }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <Skeleton v-if="loading" type="form" />

    <form v-else class="space-y-5" @submit.prevent="submit">
      <!-- ===== STEP 1: Applicant ===== -->
      <section class="card p-5 space-y-4">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-full bg-brand-600 text-white grid place-items-center text-xs font-semibold">1</div>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Abituriyent</h2>
        </div>

        <div v-if="form.applicant_id"
             class="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900">
          <div class="flex items-center gap-2 text-sm">
            <Check class="w-4 h-4 text-green-600" />
            <span class="font-medium text-slate-900 dark:text-slate-100">{{ selectedApplicantLabel }}</span>
          </div>
          <div class="flex items-center gap-2">
            <button v-if="isEdit" type="button"
                    class="text-xs font-medium px-2.5 py-1 rounded-md bg-white dark:bg-slate-800 text-brand-700 dark:text-brand-300 ring-1 ring-brand-200 dark:ring-brand-700/40 hover:bg-brand-50 dark:hover:bg-brand-900/30"
                    @click="applicantEditOpen = !applicantEditOpen">
              {{ applicantEditOpen ? 'Yopish' : "Ma'lumotlarni tahrirlash" }}
            </button>
            <button v-if="!isEdit" type="button" class="text-xs text-red-600 hover:underline" @click="clearApplicant">
              <X class="w-3.5 h-3.5 inline" /> O'zgartirish
            </button>
          </div>
        </div>

        <!-- Inline applicant editor (edit mode only) — same fields as inline create -->
        <div v-if="isEdit && applicantEditOpen" class="border-t border-slate-200 dark:border-slate-800 pt-4 space-y-3">
          <h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100">Abituriyent ma'lumotlarini tahrirlash</h3>
          <div class="grid sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Familiya *</label>
              <input :value="inlineApplicant.last_name" class="input"
                     :class="inlineErrors.last_name ? 'border-red-500' : ''"
                     placeholder="VALIYEV" @input="onInlineLast" @blur="validateInlineField('last_name')" />
              <p v-if="inlineErrors.last_name" class="mt-1 text-xs text-red-600">{{ inlineErrors.last_name }}</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Ism *</label>
              <input :value="inlineApplicant.first_name" class="input"
                     :class="inlineErrors.first_name ? 'border-red-500' : ''"
                     placeholder="ALI" @input="onInlineFirst" @blur="validateInlineField('first_name')" />
              <p v-if="inlineErrors.first_name" class="mt-1 text-xs text-red-600">{{ inlineErrors.first_name }}</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Otasining ismi</label>
              <input :value="inlineApplicant.other_name" class="input" placeholder="AKBAR O'G'LI" @input="onInlineOther" />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tug'ilgan sana *</label>
              <input v-model="inlineApplicant.birth_date" type="date" class="input"
                     :class="inlineErrors.birth_date ? 'border-red-500' : ''"
                     :max="new Date().toISOString().slice(0,10)"
                     @blur="validateInlineField('birth_date')" />
              <p v-if="inlineErrors.birth_date" class="mt-1 text-xs text-red-600">{{ inlineErrors.birth_date }}</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Jinsi *</label>
              <select v-model="inlineApplicant.gender" class="input">
                <option value="male">Erkak</option>
                <option value="female">Ayol</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Pasport</label>
              <input :value="inlineApplicant.passport_series" maxlength="9" class="input font-mono"
                     :class="inlineErrors.passport_series ? 'border-red-500' : ''"
                     :placeholder="PLACEHOLDERS.passport"
                     @input="onInlinePassport" @blur="validateInlineField('passport_series')" />
              <p v-if="inlineErrors.passport_series" class="mt-1 text-xs text-red-600">{{ inlineErrors.passport_series }}</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">PINFL</label>
              <input :value="inlineApplicant.pinfl" inputmode="numeric" maxlength="14" class="input font-mono"
                     :class="inlineErrors.pinfl ? 'border-red-500' : ''"
                     :placeholder="PLACEHOLDERS.pinfl"
                     @input="onInlinePinfl" @blur="validateInlineField('pinfl')" />
              <p v-if="inlineErrors.pinfl" class="mt-1 text-xs text-red-600">{{ inlineErrors.pinfl }}</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Qo'shimcha telefon</label>
              <input :value="inlineApplicant.additional_phone" type="tel" inputmode="tel" class="input font-mono"
                     :placeholder="PLACEHOLDERS.phoneUz" @input="onInlineAddPhone" />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Telegram username</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-mono pointer-events-none">@</span>
                <input v-model="inlineApplicant.telegram_username" class="input pl-7 font-mono" placeholder="username" />
              </div>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Millati</label>
              <input v-model="inlineApplicant.nationality" class="input" placeholder="O'zbek" />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Viloyat</label>
              <select v-model="inlineApplicant.region_id" class="input">
                <option value="">— tanlang —</option>
                <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tuman</label>
              <select v-model="inlineApplicant.district_id" class="input" :disabled="!inlineApplicant.region_id">
                <option value="">— tanlang —</option>
                <option v-for="d in inlineDistricts" :key="d.id" :value="d.id">{{ d.name }}</option>
              </select>
            </div>
            <div class="sm:col-span-2">
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Yashash manzili</label>
              <textarea v-model="inlineApplicant.address" rows="2" class="input"
                        placeholder="Mahalla yoki ko'cha nomi, uy raqami"></textarea>
            </div>
          </div>
          <p class="text-[11px] text-slate-500 dark:text-slate-400">
            O'zgarishlar pastdagi <strong>"Saqlash"</strong> tugmasini bosganingizda ariza bilan birga saqlanadi.
          </p>
        </div>

        <template v-else-if="!isEdit">
          <div class="flex gap-2">
            <div class="relative flex-1">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <input v-model="applicantSearch" class="input pl-10" placeholder="F.I.Sh., PINFL, telefon..." />
              <div v-if="applicantResults.length"
                   class="absolute z-20 mt-1 w-full card max-h-64 overflow-y-auto p-1 shadow-lg">
                <button v-for="a in applicantResults" :key="a.id" type="button"
                        class="w-full text-left px-3 py-2 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-sm"
                        @click="selectApplicant(a)">
                  <div class="font-medium text-slate-900 dark:text-slate-100">
                    {{ a.last_name }} {{ a.first_name }} {{ a.other_name || '' }}
                  </div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 font-mono">
                    PINFL: {{ a.pinfl || '—' }} · Pasport: {{ a.passport_series || '—' }}
                  </div>
                </button>
              </div>
            </div>
            <button type="button" class="btn-ghost shrink-0" @click="openInlineCreate">
              <UserPlus class="w-4 h-4" /> Yangi
            </button>
          </div>
          <p v-if="applicantSearch.length >= 2 && !applicantResults.length && !showInlineCreate"
             class="text-xs text-slate-500 dark:text-slate-400">
            Topilmadi.
            <button type="button" class="text-brand-600 hover:underline" @click="openInlineCreate">Yangi yaratish</button>
          </p>

          <div v-if="showInlineCreate" class="border-t border-slate-200 dark:border-slate-800 pt-4 space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100">Yangi abituriyent</h3>
              <button type="button" class="text-xs text-slate-500 hover:underline" @click="showInlineCreate = false">
                Yopish
              </button>
            </div>
            <div class="grid sm:grid-cols-2 gap-3">
              <div class="sm:col-span-2">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Telefon *</label>
                <input id="inline-applicant-phone" :value="inlineApplicant.phone"
                       inputmode="tel" type="tel" class="input font-mono"
                       :class="inlineErrors.phone ? 'border-red-500' : ''"
                       :placeholder="PLACEHOLDERS.phoneUz"
                       @input="onInlinePhone" @blur="validateInlineField('phone')" />
                <p v-if="inlineErrors.phone" class="mt-1 text-xs text-red-600">{{ inlineErrors.phone }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Familiya *</label>
                <input :value="inlineApplicant.last_name" class="input"
                       :class="inlineErrors.last_name ? 'border-red-500' : ''"
                       placeholder="VALIYEV" @input="onInlineLast" @blur="validateInlineField('last_name')" />
                <p v-if="inlineErrors.last_name" class="mt-1 text-xs text-red-600">{{ inlineErrors.last_name }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Ism *</label>
                <input :value="inlineApplicant.first_name" class="input"
                       :class="inlineErrors.first_name ? 'border-red-500' : ''"
                       placeholder="ALI" @input="onInlineFirst" @blur="validateInlineField('first_name')" />
                <p v-if="inlineErrors.first_name" class="mt-1 text-xs text-red-600">{{ inlineErrors.first_name }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Otasining ismi</label>
                <input :value="inlineApplicant.other_name" class="input"
                       placeholder="AKBAR O'G'LI" @input="onInlineOther" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tug'ilgan sana *</label>
                <input v-model="inlineApplicant.birth_date" type="date" class="input"
                       :class="inlineErrors.birth_date ? 'border-red-500' : ''"
                       :max="new Date().toISOString().slice(0,10)"
                       @blur="validateInlineField('birth_date')" />
                <p v-if="inlineErrors.birth_date" class="mt-1 text-xs text-red-600">{{ inlineErrors.birth_date }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Jinsi *</label>
                <select v-model="inlineApplicant.gender" class="input">
                  <option value="male">Erkak</option>
                  <option value="female">Ayol</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Pasport</label>
                <input :value="inlineApplicant.passport_series" maxlength="9"
                       class="input font-mono"
                       :class="inlineErrors.passport_series ? 'border-red-500' : ''"
                       :placeholder="PLACEHOLDERS.passport"
                       @input="onInlinePassport" @blur="validateInlineField('passport_series')" />
                <p v-if="inlineErrors.passport_series" class="mt-1 text-xs text-red-600">{{ inlineErrors.passport_series }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">PINFL</label>
                <input :value="inlineApplicant.pinfl" inputmode="numeric" maxlength="14"
                       class="input font-mono"
                       :class="inlineErrors.pinfl ? 'border-red-500' : ''"
                       :placeholder="PLACEHOLDERS.pinfl"
                       @input="onInlinePinfl" @blur="validateInlineField('pinfl')" />
                <p v-if="inlineErrors.pinfl" class="mt-1 text-xs text-red-600">{{ inlineErrors.pinfl }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Qo'shimcha telefon</label>
                <input :value="inlineApplicant.additional_phone" type="tel" inputmode="tel"
                       class="input font-mono" :placeholder="PLACEHOLDERS.phoneUz"
                       @input="onInlineAddPhone" />
                <p class="mt-1 text-[11px] text-slate-500">Ota-ona / qarindosh telefoni</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Telegram username</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-mono pointer-events-none">@</span>
                  <input v-model="inlineApplicant.telegram_username" class="input pl-7 font-mono" placeholder="username" />
                </div>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Millati</label>
                <input v-model="inlineApplicant.nationality" class="input" placeholder="O'zbek" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Viloyat</label>
                <select v-model="inlineApplicant.region_id" class="input">
                  <option value="">— tanlang —</option>
                  <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tuman</label>
                <select v-model="inlineApplicant.district_id" class="input" :disabled="!inlineApplicant.region_id">
                  <option value="">— tanlang —</option>
                  <option v-for="d in inlineDistricts" :key="d.id" :value="d.id">{{ d.name }}</option>
                </select>
              </div>
              <div class="sm:col-span-2">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Yashash manzili</label>
                <textarea v-model="inlineApplicant.address" rows="2" class="input"
                          placeholder="Mahalla yoki ko'cha nomi, uy raqami"></textarea>
              </div>
            </div>
            <div class="flex gap-2 pt-2">
              <button type="button" class="btn-primary text-sm" :disabled="creatingApplicant" @click="createApplicantInline">
                <UserPlus class="w-4 h-4" />
                {{ creatingApplicant ? "Yaratilmoqda..." : "Abituriyentni yaratish" }}
              </button>
              <button type="button" class="btn-ghost text-sm" @click="showInlineCreate = false">Bekor</button>
            </div>
          </div>
        </template>

        <div v-else class="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-sm text-slate-700 dark:text-slate-300">
          {{ selectedApplicantLabel }}
        </div>
      </section>

      <!-- ===== STEP 2: Admission type ===== -->
      <section class="card p-5 space-y-3" :class="!form.applicant_id ? 'opacity-60 pointer-events-none' : ''">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-full bg-brand-600 text-white grid place-items-center text-xs font-semibold">2</div>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Qabul turi</h2>
        </div>
        <div class="flex gap-3">
          <label class="flex-1 flex items-center gap-2 px-4 py-3 rounded-lg border cursor-pointer transition-colors"
                 :class="form.admission_type === 'yangi_qabul'
                   ? 'border-brand-600 bg-brand-50 dark:bg-brand-900/30'
                   : 'border-slate-200 dark:border-slate-800 hover:border-slate-300'">
            <input v-model="form.admission_type" type="radio" value="yangi_qabul" />
            <span class="text-sm font-medium">1-kurs (Yangi qabul)</span>
          </label>
          <label class="flex-1 flex items-center gap-2 px-4 py-3 rounded-lg border cursor-pointer transition-colors"
                 :class="form.admission_type === 'perevod'
                   ? 'border-brand-600 bg-brand-50 dark:bg-brand-900/30'
                   : 'border-slate-200 dark:border-slate-800 hover:border-slate-300'">
            <input v-model="form.admission_type" type="radio" value="perevod" />
            <span class="text-sm font-medium">Perevod</span>
          </label>
        </div>
      </section>

      <!-- ===== STEP 2.5: Diplom (1-kurs) ===== -->
      <section v-if="form.applicant_id && form.admission_type === 'yangi_qabul'"
               class="card p-5 space-y-4">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-full bg-brand-600 text-white grid place-items-center"><Award class="w-4 h-4" /></div>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Diplom (1-kurs)</h2>
        </div>

        <div v-if="myDiplom"
             class="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900">
          <div class="text-sm">
            <div class="font-medium text-slate-900 dark:text-slate-100 inline-flex items-center gap-1.5">
              <Check class="w-4 h-4 text-green-600" /> {{ myDiplom.serial_number }}
            </div>
            <div class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">{{ myDiplom.university_name }} ({{ myDiplom.graduation_year }})</div>
          </div>
        </div>

        <template v-else>
          <p v-if="!showDiplomForm" class="text-sm text-amber-700 dark:text-amber-300">
            Bu abituriyentda diplom yo'q.
            <button type="button" class="text-brand-600 hover:underline ml-1" @click="showDiplomForm = true">
              Diplom qo'shish
            </button>
          </p>

          <div v-if="showDiplomForm" class="space-y-3 border-t border-slate-200 dark:border-slate-800 pt-4">
            <div class="grid sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Diplom raqami *</label>
                <input v-model="diplomForm.serial_number" class="input font-mono"
                       :class="diplomErrors.serial_number ? 'border-red-500' : ''"
                       placeholder="DPL2024-12345" @blur="validateDiplomField('serial_number')" />
                <p v-if="diplomErrors.serial_number" class="mt-1 text-xs text-red-600">{{ diplomErrors.serial_number }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Bitirgan yil *</label>
                <input :value="diplomForm.graduation_year" inputmode="numeric" maxlength="4"
                       class="input font-mono"
                       :class="diplomErrors.graduation_year ? 'border-red-500' : ''"
                       :placeholder="PLACEHOLDERS.year"
                       @input="onGradYear" @blur="validateDiplomField('graduation_year')" />
                <p v-if="diplomErrors.graduation_year" class="mt-1 text-xs text-red-600">{{ diplomErrors.graduation_year }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Ta'lim turi *</label>
                <select v-model="diplomForm.education_type_id" class="input"
                        :class="diplomErrors.education_type_id ? 'border-red-500' : ''"
                        @blur="validateDiplomField('education_type_id')">
                  <option value="">— tanlang —</option>
                  <option v-for="t in educationTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
                <p v-if="diplomErrors.education_type_id" class="mt-1 text-xs text-red-600">{{ diplomErrors.education_type_id }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Muassasa turi *</label>
                <select v-model="diplomForm.institution_type_id" class="input"
                        :class="diplomErrors.institution_type_id ? 'border-red-500' : ''"
                        @blur="validateDiplomField('institution_type_id')">
                  <option value="">— tanlang —</option>
                  <option v-for="t in institutionTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
                <p v-if="diplomErrors.institution_type_id" class="mt-1 text-xs text-red-600">{{ diplomErrors.institution_type_id }}</p>
              </div>
              <div class="sm:col-span-2">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Universitet nomi *</label>
                <input v-model="diplomForm.university_name" class="input"
                       :class="diplomErrors.university_name ? 'border-red-500' : ''"
                       placeholder="Toshkent davlat universiteti"
                       @blur="validateDiplomField('university_name')" />
                <p v-if="diplomErrors.university_name" class="mt-1 text-xs text-red-600">{{ diplomErrors.university_name }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Viloyat *</label>
                <select v-model="diplomForm.region_id" class="input"
                        :class="diplomErrors.region_id ? 'border-red-500' : ''"
                        @blur="validateDiplomField('region_id')">
                  <option value="">— tanlang —</option>
                  <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
                <p v-if="diplomErrors.region_id" class="mt-1 text-xs text-red-600">{{ diplomErrors.region_id }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Tuman *</label>
                <select v-model="diplomForm.district_id" class="input"
                        :class="diplomErrors.district_id ? 'border-red-500' : ''"
                        :disabled="!diplomForm.region_id"
                        @blur="validateDiplomField('district_id')">
                  <option value="">— tanlang —</option>
                  <option v-for="d in diplomDistricts" :key="d.id" :value="d.id">{{ d.name }}</option>
                </select>
                <p v-if="diplomErrors.district_id" class="mt-1 text-xs text-red-600">{{ diplomErrors.district_id }}</p>
              </div>
            </div>
            <FileUpload v-model="diplomForm.diploma_file_id"
                        label="Diplom skani (PDF yoki rasm)"
                        hint="Ixtiyoriy. Diplom asl nusxasining skani yoki rasmi"
                        subdir="diploms" />
            <div class="flex gap-2 pt-2">
              <button type="button" class="btn-primary text-sm" :disabled="diplomCreating" @click="createDiplomInline">
                <Award class="w-4 h-4" />
                {{ diplomCreating ? "Saqlanmoqda..." : "Diplomni saqlash" }}
              </button>
              <button type="button" class="btn-ghost text-sm" @click="showDiplomForm = false">Bekor</button>
            </div>
          </div>
        </template>
      </section>

      <!-- Inline transfer diplom -->
      <section v-if="form.applicant_id && form.admission_type === 'perevod'"
               class="card p-5 space-y-4">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-full bg-brand-600 text-white grid place-items-center"><Award class="w-4 h-4" /></div>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Perevod diplomi</h2>
        </div>

        <div v-if="myTransferDiplom"
             class="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900">
          <div class="text-sm font-medium text-slate-900 dark:text-slate-100 inline-flex items-center gap-1.5">
            <Check class="w-4 h-4 text-green-600" /> {{ myTransferDiplom.university_name }}
          </div>
        </div>

        <template v-else>
          <p v-if="!showTransferForm" class="text-sm text-amber-700 dark:text-amber-300">
            Perevod diplomi yo'q.
            <button type="button" class="text-brand-600 hover:underline ml-1" @click="showTransferForm = true">
              Qo'shish
            </button>
          </p>

          <div v-if="showTransferForm" class="space-y-3 border-t border-slate-200 dark:border-slate-800 pt-4">
            <div class="grid sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Davlat *</label>
                <select v-model="transferForm.country_id" class="input"
                        :class="transferErrors.country_id ? 'border-red-500' : ''"
                        @blur="validateTransferField('country_id')">
                  <option value="">— tanlang —</option>
                  <option v-for="c in countries" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
                <p v-if="transferErrors.country_id" class="mt-1 text-xs text-red-600">{{ transferErrors.country_id }}</p>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Maqsadli kurs *</label>
                <select v-model="transferForm.target_course_id" class="input"
                        :class="transferErrors.target_course_id ? 'border-red-500' : ''"
                        @blur="validateTransferField('target_course_id')">
                  <option value="">— tanlang —</option>
                  <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
                <p v-if="transferErrors.target_course_id" class="mt-1 text-xs text-red-600">{{ transferErrors.target_course_id }}</p>
              </div>
              <div class="sm:col-span-2">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Universitet nomi *</label>
                <input v-model="transferForm.university_name" class="input"
                       :class="transferErrors.university_name ? 'border-red-500' : ''"
                       placeholder="Moskva davlat universiteti"
                       @blur="validateTransferField('university_name')" />
                <p v-if="transferErrors.university_name" class="mt-1 text-xs text-red-600">{{ transferErrors.university_name }}</p>
              </div>
            </div>
            <FileUpload v-model="transferForm.transcript_file_id"
                        label="Transkript / akademik ma'lumotnoma (PDF yoki rasm)"
                        hint="Ixtiyoriy. Transkript yoki akademik ma'lumotnoma skani"
                        subdir="transfer-diploms" />
            <div class="flex gap-2 pt-2">
              <button type="button" class="btn-primary text-sm" :disabled="transferCreating" @click="createTransferInline">
                <Award class="w-4 h-4" />
                {{ transferCreating ? "Saqlanmoqda..." : "Diplomni saqlash" }}
              </button>
              <button type="button" class="btn-ghost text-sm" @click="showTransferForm = false">Bekor</button>
            </div>
          </div>
        </template>
      </section>

      <!-- ===== STEP 3: Cascading branch → level → form → program ===== -->
      <section class="card p-5 space-y-4" :class="!form.applicant_id ? 'opacity-60 pointer-events-none' : ''">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-full bg-brand-600 text-white grid place-items-center text-xs font-semibold">3</div>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Yo'nalish tanlash</h2>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Filial *</label>
          <select v-model="form.branch_id" class="input" :class="errors.branch_id ? 'border-red-500' : ''">
            <option value="">— filial tanlang —</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
          <p v-if="errors.branch_id" class="mt-1 text-xs text-red-600">{{ errors.branch_id }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ta'lim darajasi *</label>
          <select v-model="form.education_level_id" class="input"
                  :class="errors.education_level_id ? 'border-red-500' : ''"
                  :disabled="!form.branch_id">
            <option value="">{{ levelPlaceholder }}</option>
            <option v-for="l in availableLevels" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
          <p v-if="errors.education_level_id" class="mt-1 text-xs text-red-600">{{ errors.education_level_id }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ta'lim shakli *</label>
          <select v-model="form.education_form_id" class="input"
                  :class="errors.education_form_id ? 'border-red-500' : ''"
                  :disabled="!form.education_level_id">
            <option value="">{{ formPlaceholder }}</option>
            <option v-for="f in availableForms" :key="f.id" :value="f.id">{{ f.name }}</option>
          </select>
          <p v-if="errors.education_form_id" class="mt-1 text-xs text-red-600">{{ errors.education_form_id }}</p>
          <p v-else-if="form.admission_type === 'yangi_qabul'"
             class="mt-1 text-xs text-slate-500 dark:text-slate-400">
            1-kursga topshirish faqat Kunduzgi shaklda mumkin.
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yo'nalish *</label>
          <select v-model="form.program_id" class="input"
                  :class="errors.program_id ? 'border-red-500' : ''"
                  :disabled="!form.education_form_id">
            <option value="">{{ programPlaceholder }}</option>
            <option v-for="p in availablePrograms" :key="p.id" :value="p.id">
              {{ p.code }} · {{ p.name }}
            </option>
          </select>
          <p v-if="errors.program_id" class="mt-1 text-xs text-red-600">{{ errors.program_id }}</p>
        </div>

        <div v-if="selectedProgram"
             class="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3 text-xs space-y-1">
          <div class="font-medium text-slate-900 dark:text-slate-100">{{ selectedProgram.name }}</div>
          <div class="text-slate-600 dark:text-slate-400">
            Yillik to'lov:
            <span class="font-medium text-slate-900 dark:text-slate-100">
              {{ Number(selectedProgram.tuition_fee).toLocaleString('uz-UZ').replace(/,/g, ' ') }} so'm
            </span>
            · Muddati: <span class="font-medium text-slate-900 dark:text-slate-100">{{ (selectedProgram as any).study_duration_years }} yil</span>
          </div>
        </div>

        <div v-if="form.admission_type === 'perevod'" class="border-t border-slate-200 dark:border-slate-800 pt-4">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Maqsadli kurs *</label>
          <select v-model="form.course_id" class="input" :class="errors.course_id ? 'border-red-500' : ''">
            <option value="">— kursni tanlang —</option>
            <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <p v-if="errors.course_id" class="mt-1 text-xs text-red-600">{{ errors.course_id }}</p>
          <p v-if="errors.transfer_diplom_id" class="mt-1 text-xs text-red-600">{{ errors.transfer_diplom_id }}</p>
        </div>
        <p v-if="form.admission_type === 'yangi_qabul' && errors.diplom_id"
           class="text-xs text-red-600">{{ errors.diplom_id }}</p>
      </section>

      <section class="card p-5 space-y-3" :class="!form.applicant_id ? 'opacity-60 pointer-events-none' : ''">
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300">Eslatma (ixtiyoriy)</label>
        <textarea v-model="form.notes" class="input" rows="2" placeholder="Operator yozuvi..."></textarea>
      </section>

      <div class="flex gap-3">
        <button type="submit" class="btn-primary" :disabled="saving || !form.applicant_id">
          <Save class="w-4 h-4" />
          {{ saving ? 'Saqlanmoqda...' : (isEdit ? 'Yangilash' : 'Arizani yaratish') }}
        </button>
        <button type="button" class="btn-ghost" @click="router.push(`${panelPrefix}/applications`)">Bekor qilish</button>
      </div>
    </form>
  </div>
</template>
