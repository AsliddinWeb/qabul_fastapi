<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import { ArrowLeft, FileText, Save } from 'lucide-vue-next'
import { staffApi } from '@/api/staff.api'
import type { ApplicantDetailed, ApplicantBase } from '@/api/applicants.api'
import { adminApi, type RegionRead, type DistrictRead, type CountryRead } from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
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

const data = ref<ApplicantDetailed | null>(null)
const loading = ref(true)
const saving = ref(false)
const errors = ref<Record<string, string>>({})

const personal = reactive<ApplicantBase>({
  last_name: '', first_name: '', other_name: '',
  birth_date: '', gender: 'male',
  passport_series: '', pinfl: '',
  region_id: null, district_id: null,
  address: '', nationality: "O'zbek",
  additional_phone: '', telegram_username: '',
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
    })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  countries.value = await adminApi.countries.list().catch(() => [])
  const uz = countries.value.find((c) => c.name === "O'zbekiston") || countries.value[0]
  if (uz) regions.value = await adminApi.regions.list(uz.id).catch(() => [])
  await load()
  if (personal.region_id) {
    districts.value = await adminApi.districts.list(personal.region_id).catch(() => [])
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
      <button v-if="!isAccountantPanel" class="btn-primary" @click="generateContract">
        <FileText class="w-4 h-4" /> Shartnoma yaratish
      </button>
    </PageHeader>

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
      </div>
      <button v-if="!isAccountantPanel" class="btn-primary" :disabled="saving" @click="saveInfo">
        <Save class="w-4 h-4" /> {{ saving ? 'Saqlanmoqda...' : 'Saqlash' }}
      </button>
    </section>

    <!-- Login info card -->
    <LoginInfoCard v-if="data?.user_id" :user-id="data.user_id" />

    <section class="card p-4 sm:p-6">
      <h3 class="font-semibold text-slate-900 dark:text-slate-100 mb-2">Diplom va arizalar</h3>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        Diplom (1-kurs) yoki perevod diplomi alohida sahifalarda boshqariladi.
      </p>
    </section>
  </div>
</template>
