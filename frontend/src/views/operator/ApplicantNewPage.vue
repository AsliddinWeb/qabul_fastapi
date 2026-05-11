<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Save, UserPlus } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { staffApi, type OperatorApplicantCreate } from '@/api/staff.api'
import { adminApi, type RegionRead, type DistrictRead, type CountryRead } from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import {
  PLACEHOLDERS,
  formatNameUpper,
  formatPassport,
  formatPhone,
  compactPhone,
  formatPinfl,
  passport as vPassport,
  phoneUz as vPhone,
  pinfl as vPinfl,
} from '@/utils/validators'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const toast = useToast()

// Detect panel prefix from current URL so admin stays in admin, operator stays in operator.
const panelPrefix = computed(() => {
  if (route.path.startsWith('/admin/')) return '/admin'
  return '/operator'
})

const form = reactive<OperatorApplicantCreate>({
  phone: '+998',
  last_name: '',
  first_name: '',
  other_name: '',
  birth_date: '',
  gender: 'male',
  passport_series: '',
  pinfl: '',
  region_id: null,
  district_id: null,
  address: '',
  nationality: "O'zbek",
  additional_phone: '',
  telegram_username: '',
})

const countries = ref<CountryRead[]>([])
const regions = ref<RegionRead[]>([])
const districts = ref<DistrictRead[]>([])
const saving = ref(false)
const loading = ref(true)
const errors = ref<Record<string, string>>({})

onMounted(async () => {
  try {
    countries.value = await adminApi.countries.list()
    const uz = countries.value.find((c) => c.name === "O'zbekiston") || countries.value[0]
    if (uz) regions.value = await adminApi.regions.list(uz.id)
  } finally {
    loading.value = false
  }
})

watch(() => form.region_id, async (rid) => {
  form.district_id = null
  if (rid) districts.value = await adminApi.districts.list(rid)
  else districts.value = []
})

function validateField(field: string) {
  const ne = { ...errors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'phone':           err = vPhone(form.phone); break
    case 'last_name':       err = form.last_name.trim() ? null : 'Familiya majburiy'; break
    case 'first_name':      err = form.first_name.trim() ? null : 'Ism majburiy'; break
    case 'birth_date':      err = form.birth_date ? null : "Tug'ilgan sana majburiy"; break
    case 'passport_series': err = vPassport(form.passport_series || ''); break
    case 'pinfl':           err = vPinfl(form.pinfl || ''); break
    case 'additional_phone':err = form.additional_phone ? vPhone(form.additional_phone) : null; break
    case 'telegram_username':
      err = form.telegram_username && !/^[a-zA-Z][a-zA-Z0-9_]{3,31}$/.test(form.telegram_username.replace(/^@/, ''))
        ? "Faqat lotin harf, raqam va _ (4-32 belgi)"
        : null
      break
  }
  if (err) ne[field] = err
  errors.value = ne
}

function onPhone(e: Event)    { form.phone = formatPhone((e.target as HTMLInputElement).value); validateField('phone') }
function onLast(e: Event)     { form.last_name = formatNameUpper((e.target as HTMLInputElement).value); validateField('last_name') }
function onFirst(e: Event)    { form.first_name = formatNameUpper((e.target as HTMLInputElement).value); validateField('first_name') }
function onOther(e: Event)    { form.other_name = formatNameUpper((e.target as HTMLInputElement).value) }
function onPassport(e: Event) { form.passport_series = formatPassport((e.target as HTMLInputElement).value); validateField('passport_series') }
function onPinfl(e: Event)    { form.pinfl = formatPinfl((e.target as HTMLInputElement).value); validateField('pinfl') }
function onAddPhone(e: Event) { form.additional_phone = formatPhone((e.target as HTMLInputElement).value); validateField('additional_phone') }

function validateAll(): boolean {
  ;['phone', 'last_name', 'first_name', 'birth_date', 'passport_series', 'pinfl', 'additional_phone', 'telegram_username'].forEach(validateField)
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validateAll()) {
    toast.error("Maydonlarni to'g'ri to'ldiring")
    return
  }
  saving.value = true
  try {
    const payload: OperatorApplicantCreate = {
      ...form,
      phone: compactPhone(form.phone),
      passport_series: form.passport_series ? form.passport_series.toUpperCase() : null,
      pinfl: form.pinfl || null,
      other_name: form.other_name || null,
      address: form.address || null,
      additional_phone: form.additional_phone ? compactPhone(form.additional_phone) : null,
      telegram_username: form.telegram_username ? form.telegram_username.trim().replace(/^@/, '') : null,
    }
    const created = await staffApi.applicants.operatorCreate(payload)
    toast.success("Abituriyent yaratildi")
    router.push(`${panelPrefix.value}/applicants/${created.id}`)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik yuz berdi")
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Yangi abituriyent"
      subtitle="Abituriyent shaxsan kelganida operator tomonidan qo'lda ro'yxatga olish."
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'Abituriyentlar', to: panelPrefix + '/applicants' }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <Skeleton v-if="loading" type="form" :rows="12" />

    <form v-else class="card p-6 space-y-5" @submit.prevent="submit">
      <div>
        <label class="block text-sm font-medium mb-1">Telefon raqam *</label>
        <input :value="form.phone" type="tel" inputmode="tel"
               class="input font-mono"
               :class="errors.phone ? 'border-red-500' : ''"
               :placeholder="PLACEHOLDERS.phoneUz"
               @input="onPhone" @blur="validateField('phone')" />
        <p v-if="errors.phone" class="mt-1 text-xs text-red-600">{{ errors.phone }}</p>
        <p v-else class="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Abituriyent shu raqam orqali OTP bilan tizimga kirishi mumkin
        </p>
      </div>

      <div class="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Familiya *</label>
          <input :value="form.last_name" class="input" placeholder="VALIYEV"
                 :class="errors.last_name ? 'border-red-500' : ''"
                 @input="onLast" @blur="validateField('last_name')" />
          <p v-if="errors.last_name" class="mt-1 text-xs text-red-600">{{ errors.last_name }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Ism *</label>
          <input :value="form.first_name" class="input" placeholder="ALI"
                 :class="errors.first_name ? 'border-red-500' : ''"
                 @input="onFirst" @blur="validateField('first_name')" />
          <p v-if="errors.first_name" class="mt-1 text-xs text-red-600">{{ errors.first_name }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Otasining ismi</label>
          <input :value="form.other_name" class="input" placeholder="AKBAR O'G'LI" @input="onOther" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Tug'ilgan sana *</label>
          <input v-model="form.birth_date" type="date" class="input"
                 :class="errors.birth_date ? 'border-red-500' : ''"
                 :max="new Date().toISOString().slice(0,10)"
                 @blur="validateField('birth_date')" />
          <p v-if="errors.birth_date" class="mt-1 text-xs text-red-600">{{ errors.birth_date }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Jinsi *</label>
          <select v-model="form.gender" class="input">
            <option value="male">Erkak</option>
            <option value="female">Ayol</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Millati</label>
          <input v-model="form.nationality" class="input" placeholder="O'zbek" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Pasport seriyasi</label>
          <input :value="form.passport_series" class="input font-mono" maxlength="9"
                 :class="errors.passport_series ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.passport"
                 @input="onPassport" @blur="validateField('passport_series')" />
          <p v-if="errors.passport_series" class="mt-1 text-xs text-red-600">{{ errors.passport_series }}</p>
          <p v-else class="mt-1 text-xs text-slate-500 dark:text-slate-400">2 lotin harf + 7 raqam</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">JSHSHIR (PINFL)</label>
          <input :value="form.pinfl" class="input font-mono" inputmode="numeric" maxlength="14"
                 :class="errors.pinfl ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.pinfl"
                 @input="onPinfl" @blur="validateField('pinfl')" />
          <p v-if="errors.pinfl" class="mt-1 text-xs text-red-600">{{ errors.pinfl }}</p>
          <p v-else class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ (form.pinfl || '').length }}/14</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Viloyat</label>
          <select v-model="form.region_id" class="input">
            <option :value="null">— tanlang —</option>
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Tuman</label>
          <select v-model="form.district_id" class="input" :disabled="!form.region_id">
            <option :value="null">— tanlang —</option>
            <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Qo'shimcha telefon</label>
          <input :value="form.additional_phone" type="tel" inputmode="tel"
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
            <input v-model="form.telegram_username" class="input pl-7 font-mono"
                   :class="errors.telegram_username ? 'border-red-500' : ''"
                   placeholder="username"
                   @blur="validateField('telegram_username')" />
          </div>
          <p v-if="errors.telegram_username" class="mt-1 text-xs text-red-600">{{ errors.telegram_username }}</p>
          <p v-else class="mt-1 text-[11px] text-slate-500">Ixtiyoriy. Aloqa uchun ikkinchi yo'l.</p>
        </div>
        <div class="sm:col-span-2 lg:col-span-3 xl:col-span-4">
          <label class="block text-sm font-medium mb-1">Manzil</label>
          <input v-model="form.address" class="input" placeholder="Mahalla yoki ko'cha nomi, uy raqami" />
        </div>
      </div>

      <div class="flex items-center gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
        <button type="submit" class="btn-primary" :disabled="saving">
          <Save class="w-4 h-4" /> {{ saving ? 'Saqlanmoqda...' : "Yaratish" }}
        </button>
        <button type="button" class="btn-ghost" @click="router.back()">Bekor qilish</button>
      </div>
    </form>
  </div>
</template>
