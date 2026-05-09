<script setup lang="ts">
import { onMounted, reactive, ref, watch, nextTick } from 'vue'
import { Plus, Award, Pencil, Trash2, Search, X, UserPlus, FileText, ExternalLink } from 'lucide-vue-next'
import { fileUrl } from '@/utils/files'
import { AxiosError } from 'axios'
import { adminApi, type NamedRecord, type RegionRead, type DistrictRead } from '@/api/admin.api'
import EmptyState from '@/components/ui/EmptyState.vue'
import FileUpload from '@/components/ui/FileUpload.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { PLACEHOLDERS, formatYear, year as vYear } from '@/utils/validators'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

interface DiplomItem {
  id: string
  user_id: string
  serial_number: string
  education_type_id: string
  institution_type_id: string
  university_name: string
  graduation_year: string
  region_id: string
  district_id: string
  diploma_file_id?: string | null
  created_at: string
  updated_at: string
  // Server-joined applicant info
  applicant_last_name?: string | null
  applicant_first_name?: string | null
  applicant_other_name?: string | null
  applicant_pinfl?: string | null
  applicant_passport_series?: string | null
}

const toast = useToast()
const { ask } = useConfirm()

const items = ref<DiplomItem[]>([])
const total = ref(0)
const loading = ref(false)
const filters = reactive({ search: '', page: 1, size: 50 })

const educationTypes = ref<NamedRecord[]>([])
const institutionTypes = ref<NamedRecord[]>([])
const regions = ref<RegionRead[]>([])
const districts = ref<DistrictRead[]>([])

// Cache user info for displaying applicants in list rows
const userCache = ref<Record<string, any>>({})

const showForm = ref(false)
const editing = ref<DiplomItem | null>(null)
const saving = ref(false)
const errors = ref<Record<string, string>>({})

const form = reactive({
  user_id: '',
  serial_number: '',
  education_type_id: '',
  institution_type_id: '',
  university_name: '',
  graduation_year: '',
  region_id: '',
  district_id: '',
  diploma_file_id: null as string | null,
})

// Applicant search state
const applicantSearch = ref('')
const applicantResults = ref<any[]>([])
const selectedApplicant = ref<any | null>(null)

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

function selectApplicant(a: any) {
  selectedApplicant.value = a
  form.user_id = a.user_id
  applicantSearch.value = ''
  applicantResults.value = []
  // Cache for list display
  userCache.value[a.user_id] = a
  validateField('user_id')
}

function clearApplicant() {
  selectedApplicant.value = null
  form.user_id = ''
}

watch(() => form.region_id, async (rid) => {
  if (!editing.value) form.district_id = ''
  districts.value = rid ? await adminApi.districts.list(rid) : []
})

async function load() {
  loading.value = true
  try {
    const res = await adminApi.diploms.list({
      search: filters.search || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items as DiplomItem[]
    total.value = res.total
    // Cache from embedded applicant fields (used in delete confirm + edit display)
    for (const d of items.value) {
      if (d.applicant_last_name) {
        userCache.value[d.user_id] = {
          user_id: d.user_id,
          last_name: d.applicant_last_name,
          first_name: d.applicant_first_name,
          other_name: d.applicant_other_name,
          pinfl: d.applicant_pinfl,
          passport_series: d.applicant_passport_series,
        }
      }
    }
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

async function loadLookups() {
  const [et, it, c] = await Promise.all([
    adminApi.educationTypes.list(),
    adminApi.institutionTypes.list(),
    adminApi.countries.list(),
  ])
  educationTypes.value = et
  institutionTypes.value = it
  const uz = c.find((x) => x.name === "O'zbekiston") || c[0]
  if (uz) regions.value = await adminApi.regions.list(uz.id)
}

let listSearchTimer: ReturnType<typeof setTimeout> | null = null
watch(() => filters.search, () => {
  if (listSearchTimer) clearTimeout(listSearchTimer)
  listSearchTimer = setTimeout(() => { filters.page = 1; load() }, 300)
})
watch(() => filters.page, load)

onMounted(async () => {
  await loadLookups()
  await load()
})

function openCreate() {
  editing.value = null
  selectedApplicant.value = null
  applicantSearch.value = ''
  Object.assign(form, {
    user_id: '', serial_number: '',
    education_type_id: educationTypes.value[0]?.id || '',
    institution_type_id: institutionTypes.value[0]?.id || '',
    university_name: '', graduation_year: '',
    region_id: '',
    district_id: '',
    diploma_file_id: null,
  })
  errors.value = {}
  showForm.value = true
}

async function openEdit(d: DiplomItem) {
  editing.value = d
  selectedApplicant.value = userCache.value[d.user_id] || null
  Object.assign(form, {
    user_id: d.user_id,
    serial_number: d.serial_number,
    education_type_id: d.education_type_id,
    institution_type_id: d.institution_type_id,
    university_name: d.university_name,
    graduation_year: d.graduation_year,
    region_id: d.region_id,
    district_id: d.district_id,
    diploma_file_id: (d as any).diploma_file_id ?? null,
  })
  if (d.region_id) districts.value = await adminApi.districts.list(d.region_id)
  errors.value = {}
  showForm.value = true
}

function onYearInput(e: Event) {
  form.graduation_year = formatYear((e.target as HTMLInputElement).value)
  validateField('graduation_year')
}

function validateField(field: string) {
  const ne = { ...errors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'user_id':            err = !editing.value && !form.user_id ? "Abituriyentni tanlang" : null; break
    case 'serial_number':      err = form.serial_number.trim() ? null : "Diplom seriya raqamini kiriting"; break
    case 'education_type_id':  err = form.education_type_id ? null : "Ta'lim turini tanlang"; break
    case 'institution_type_id':err = form.institution_type_id ? null : "Muassasa turini tanlang"; break
    case 'university_name':    err = form.university_name.trim() ? null : "Universitet nomini kiriting"; break
    case 'graduation_year':    err = vYear(form.graduation_year); break
    case 'region_id':          err = form.region_id ? null : "Viloyatni tanlang"; break
    case 'district_id':        err = form.district_id ? null : "Tumanni tanlang"; break
  }
  if (err) ne[field] = err
  errors.value = ne
}

function validate(): boolean {
  ;['user_id', 'serial_number', 'education_type_id', 'institution_type_id',
    'university_name', 'graduation_year', 'region_id', 'district_id'].forEach(validateField)
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) {
    toast.error("Maydonlarni to'ldiring")
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      const { user_id, ...payload } = form
      await adminApi.diploms.update(editing.value.id, payload)
      toast.success("Diplom yangilandi")
    } else {
      await adminApi.diploms.create({ ...form })
      toast.success("Diplom qo'shildi")
    }
    showForm.value = false
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    saving.value = false
  }
}

async function remove(d: DiplomItem) {
  const owner = userCache.value[d.user_id]
  const ownerName = owner ? `${owner.last_name} ${owner.first_name}` : d.serial_number
  const ok = await ask({
    title: "Diplomni o'chirish",
    message: `${ownerName} ning diplomi (${d.serial_number}) o'chirilsinmi?`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.diploms.delete(d.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi")
  }
}

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))
const lookupName = (list: NamedRecord[], id: string) => list.find((x) => x.id === id)?.name || ''
function applicantLabel(uid: string): string {
  const u = userCache.value[uid]
  if (!u) return uid.slice(0, 8) + '…'
  return `${u.last_name || ''} ${u.first_name || ''}`.trim() || uid.slice(0, 8) + '…'
}
function avatarInitials(uid: string): string {
  const u = userCache.value[uid]
  if (!u) return '?'
  return ((u.last_name?.[0] || '') + (u.first_name?.[0] || '')).toUpperCase() || '?'
}
const AVATAR_COLORS = [
  'from-blue-400 to-blue-600',
  'from-purple-400 to-purple-600',
  'from-pink-400 to-rose-600',
  'from-emerald-400 to-teal-600',
  'from-amber-400 to-orange-600',
]
function avatarColor(uid: string): string {
  const h = uid.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}
</script>

<template>
  <div>
    <PageHeader
      title="Diplomlar (1-kurs)"
      :subtitle="`Yangi qabul abituriyentlarining diplomlari · Jami ${total}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Qabul jarayoni' }]"
    >
      <button class="btn-primary" @click="openCreate">
        <Plus class="w-4 h-4" /> Yangi diplom
      </button>
    </PageHeader>

    <div class="filter-bar">
      <div class="flex-1 min-w-[260px]">
        <label class="field-label">Qidirish</label>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input v-model="filters.search" class="input pl-10" placeholder="Diplom raqami yoki universitet..." />
        </div>
      </div>
    </div>

    <!-- Form (modal-ish inline panel) -->
    <form v-if="showForm" class="card p-6 mb-4 space-y-5" @submit.prevent="submit">
      <h2 class="section-title">{{ editing ? "Diplomni tahrirlash" : "Yangi diplom" }}</h2>

      <!-- Applicant section -->
      <div>
        <label class="field-label">Abituriyent *</label>

        <div v-if="selectedApplicant"
             class="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900">
          <div class="flex items-center gap-3">
            <div class="avatar bg-gradient-to-br text-white" :class="avatarColor(form.user_id)">
              {{ avatarInitials(form.user_id) }}
            </div>
            <div class="text-sm">
              <div class="font-medium text-slate-900 dark:text-slate-100">
                {{ selectedApplicant.last_name }} {{ selectedApplicant.first_name }}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 font-mono">
                PINFL: {{ selectedApplicant.pinfl || '—' }} · Pasport: {{ selectedApplicant.passport_series || '—' }}
              </div>
            </div>
          </div>
          <button v-if="!editing" type="button" class="text-xs text-red-600 hover:underline" @click="clearApplicant">
            <X class="w-3.5 h-3.5 inline" /> O'zgartirish
          </button>
        </div>

        <div v-else-if="!editing" class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input v-model="applicantSearch" class="input pl-10"
                 :class="errors.user_id ? 'border-red-500' : ''"
                 placeholder="F.I.Sh., PINFL, pasport bo'yicha qidiring..." />
          <div v-if="applicantResults.length"
               class="absolute z-20 mt-1 w-full card max-h-64 overflow-y-auto p-1 shadow-lg">
            <button v-for="a in applicantResults" :key="a.id" type="button"
                    class="w-full text-left px-3 py-2 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-sm flex items-center gap-3"
                    @click="selectApplicant(a)">
              <div class="avatar bg-gradient-to-br text-white" :class="avatarColor(a.user_id)">
                {{ ((a.last_name?.[0] || '') + (a.first_name?.[0] || '')).toUpperCase() || '?' }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                  {{ a.last_name }} {{ a.first_name }} {{ a.other_name || '' }}
                </div>
                <div class="text-xs text-slate-500 dark:text-slate-400 font-mono truncate">
                  PINFL: {{ a.pinfl || '—' }} · Pasport: {{ a.passport_series || '—' }}
                </div>
              </div>
            </button>
          </div>
        </div>

        <p v-if="errors.user_id" class="field-error">{{ errors.user_id }}</p>
      </div>

      <!-- Diplom fields -->
      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="field-label">Diplom seriya raqami *</label>
          <input v-model="form.serial_number" class="input font-mono"
                 :class="errors.serial_number ? 'border-red-500' : ''"
                 placeholder="DPL2024-12345" @blur="validateField('serial_number')" />
          <p v-if="errors.serial_number" class="field-error">{{ errors.serial_number }}</p>
          <p v-else class="field-hint">Hujjatdagi rasmiy raqam</p>
        </div>
        <div>
          <label class="field-label">Bitirgan yil *</label>
          <input :value="form.graduation_year" inputmode="numeric" maxlength="4"
                 class="input font-mono"
                 :class="errors.graduation_year ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.year"
                 @input="onYearInput" @blur="validateField('graduation_year')" />
          <p v-if="errors.graduation_year" class="field-error">{{ errors.graduation_year }}</p>
        </div>
        <div>
          <label class="field-label">Ta'lim turi *</label>
          <select v-model="form.education_type_id" class="input"
                  :class="errors.education_type_id ? 'border-red-500' : ''"
                  @blur="validateField('education_type_id')">
            <option value="">— tanlang —</option>
            <option v-for="t in educationTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <p v-if="errors.education_type_id" class="field-error">{{ errors.education_type_id }}</p>
        </div>
        <div>
          <label class="field-label">Muassasa turi *</label>
          <select v-model="form.institution_type_id" class="input"
                  :class="errors.institution_type_id ? 'border-red-500' : ''"
                  @blur="validateField('institution_type_id')">
            <option value="">— tanlang —</option>
            <option v-for="t in institutionTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <p v-if="errors.institution_type_id" class="field-error">{{ errors.institution_type_id }}</p>
        </div>
        <div class="sm:col-span-2">
          <label class="field-label">Universitet nomi *</label>
          <input v-model="form.university_name" class="input"
                 :class="errors.university_name ? 'border-red-500' : ''"
                 placeholder="Toshkent davlat universiteti"
                 @blur="validateField('university_name')" />
          <p v-if="errors.university_name" class="field-error">{{ errors.university_name }}</p>
        </div>
        <div>
          <label class="field-label">Viloyat *</label>
          <select v-model="form.region_id" class="input"
                  :class="errors.region_id ? 'border-red-500' : ''"
                  @blur="validateField('region_id')">
            <option value="">— tanlang —</option>
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
          <p v-if="errors.region_id" class="field-error">{{ errors.region_id }}</p>
        </div>
        <div>
          <label class="field-label">Tuman *</label>
          <select v-model="form.district_id" class="input"
                  :class="errors.district_id ? 'border-red-500' : ''"
                  :disabled="!form.region_id"
                  @blur="validateField('district_id')">
            <option value="">— tanlang —</option>
            <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
          <p v-if="errors.district_id" class="field-error">{{ errors.district_id }}</p>
        </div>
      </div>

      <div>
        <label class="field-label">Diplom skani (PDF yoki rasm)</label>
        <a v-if="editing && editing.diploma_file_id"
           :href="fileUrl(editing.diploma_file_id)!" target="_blank" rel="noopener"
           class="inline-flex items-center gap-2 mb-2 px-3 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 hover:border-brand-400 hover:text-brand-600 transition-colors">
          <FileText class="w-4 h-4" />
          Hozirgi faylni ochish
          <ExternalLink class="w-3.5 h-3.5" />
        </a>
        <FileUpload v-model="form.diploma_file_id"
                    hint="Ixtiyoriy. Diplom asl nusxasining skani yoki rasmi"
                    subdir="diploms" />
      </div>

      <div class="flex gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
        <button type="submit" class="btn-primary" :disabled="saving">
          {{ saving ? 'Saqlanmoqda...' : (editing ? "Yangilash" : "Yaratish") }}
        </button>
        <button type="button" class="btn-ghost" @click="showForm = false">Bekor qilish</button>
      </div>
    </form>

    <Skeleton v-if="loading" type="table" />

    <div v-else-if="!items.length" class="card p-6">
      <EmptyState :icon="Award" title="Diplomlar yo'q"
                  subtitle="Birinchi diplom qo'shing yoki ariza yaratish jarayonida diplomni inline qo'shing">
        <button class="btn-primary mt-4" @click="openCreate"><Plus class="w-4 h-4" /> Yangi diplom</button>
      </EmptyState>
    </div>

    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Abituriyent</th>
            <th class="w-44">Diplom №</th>
            <th>Universitet</th>
            <th class="w-32">Yil</th>
            <th class="w-40">Turi</th>
            <th class="w-28 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in items" :key="d.id" class="cursor-pointer" @click="openEdit(d)">
            <td>
              <div class="flex items-center gap-3">
                <div class="avatar bg-gradient-to-br text-white" :class="avatarColor(d.user_id)">
                  {{ ((d.applicant_last_name?.[0] || '') + (d.applicant_first_name?.[0] || '')).toUpperCase() || '?' }}
                </div>
                <div class="min-w-0">
                  <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                    {{ d.applicant_last_name }} {{ d.applicant_first_name }}
                  </div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 font-mono truncate">
                    {{ d.applicant_pinfl || '—' }}
                  </div>
                </div>
              </div>
            </td>
            <td>
              <span class="pill font-mono">{{ d.serial_number }}</span>
            </td>
            <td class="text-slate-700 dark:text-slate-300">{{ d.university_name }}</td>
            <td class="text-slate-600 dark:text-slate-400">{{ d.graduation_year }}</td>
            <td class="text-xs text-slate-500 dark:text-slate-400">{{ lookupName(educationTypes, d.education_type_id) }}</td>
            <td class="text-right" @click.stop>
              <div class="inline-flex gap-1">
                <button class="icon-btn" title="Tahrirlash" @click="openEdit(d)">
                  <Pencil class="w-4 h-4" />
                </button>
                <button class="icon-btn-danger" title="O'chirish" @click="remove(d)">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="items.length" class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">
          Sahifa <strong class="text-slate-700 dark:text-slate-300">{{ filters.page }}</strong> / {{ lastPage() }}
        </div>
        <div class="flex gap-2">
          <button class="btn-outline btn-sm" :disabled="filters.page <= 1" @click="filters.page--">‹ Oldingi</button>
          <button class="btn-outline btn-sm" :disabled="filters.page >= lastPage()" @click="filters.page++">Keyingi ›</button>
        </div>
      </div>
    </div>
  </div>
</template>
