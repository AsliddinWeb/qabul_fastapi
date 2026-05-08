<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { AxiosError } from 'axios'
import { Save, User as UserIcon } from 'lucide-vue-next'
import {
  applicantsApi,
  type ApplicantBase,
  type ApplicantDetailed,
} from '@/api/applicants.api'
import { adminApi, type RegionRead, type DistrictRead, type CountryRead } from '@/api/admin.api'

const profile = ref<ApplicantDetailed | null>(null)
const loading = ref(true)
const saving = ref(false)
const message = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

const personal = reactive<ApplicantBase>({
  last_name: '', first_name: '', other_name: '',
  birth_date: '', gender: 'male',
  passport_series: '', pinfl: '',
  region_id: null, district_id: null,
  address: '', nationality: "O'zbek",
  additional_phone: '', email: null,
})

const countries = ref<CountryRead[]>([])
const regions = ref<RegionRead[]>([])
const districts = ref<DistrictRead[]>([])

async function load() {
  loading.value = true
  try {
    profile.value = await applicantsApi.me()
    Object.assign(personal, {
      last_name: profile.value.last_name,
      first_name: profile.value.first_name,
      other_name: profile.value.other_name || '',
      birth_date: profile.value.birth_date,
      gender: profile.value.gender,
      passport_series: profile.value.passport_series || '',
      pinfl: profile.value.pinfl || '',
      region_id: profile.value.region_id || null,
      district_id: profile.value.district_id || null,
      address: profile.value.address || '',
      nationality: profile.value.nationality || "O'zbek",
      additional_phone: profile.value.additional_phone || '',
      email: profile.value.email || null,
    })
  } catch {
    /* not yet created */
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  countries.value = await adminApi.countries.list().catch(() => [])
  const uz = countries.value.find((c) => c.name === "O'zbekiston") || countries.value[0]
  if (uz) {
    regions.value = await adminApi.regions.list(uz.id).catch(() => [])
  }
  await load()
  if (personal.region_id) {
    districts.value = await adminApi.districts.list(personal.region_id).catch(() => [])
  }
})

watch(() => personal.region_id, async (rid) => {
  if (rid) districts.value = await adminApi.districts.list(rid).catch(() => [])
  else districts.value = []
})

function toast(text: string, type: 'ok' | 'err' = 'ok') {
  message.value = { type, text }
  setTimeout(() => { message.value = null }, 3000)
}

async function savePersonal() {
  saving.value = true
  try {
    if (profile.value) await applicantsApi.updateMe(personal)
    else                 await applicantsApi.createMe(personal)
    toast("Ma'lumotlar saqlandi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast(ax.response?.data?.error?.message || 'Xatolik', 'err')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-8">
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Mening ma'lumotlarim</h1>
      <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
        Shaxsiy ma'lumotlar, pasport ma'lumotlari (XX1234567) va PINFL.
      </p>
    </div>

    <transition
      enter-active-class="transition-opacity"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="message"
           class="text-sm rounded-lg p-3"
           :class="message.type === 'ok'
             ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300'
             : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'">
        {{ message.text }}
      </div>
    </transition>

    <section class="card p-6 space-y-5">
      <header class="flex items-center gap-2">
        <UserIcon class="w-5 h-5 text-brand-600" />
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Shaxsiy ma'lumotlar</h2>
      </header>
      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Familiya *</label>
          <input v-model="personal.last_name" class="input uppercase" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ism *</label>
          <input v-model="personal.first_name" class="input uppercase" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Otasining ismi</label>
          <input v-model="personal.other_name" class="input uppercase" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Tug'ilgan sana *</label>
          <input v-model="personal.birth_date" type="date" class="input" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Jinsi *</label>
          <select v-model="personal.gender" class="input">
            <option value="male">Erkak</option>
            <option value="female">Ayol</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Millati</label>
          <input v-model="personal.nationality" class="input" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Pasport (AA1234567)</label>
          <input v-model="personal.passport_series" class="input uppercase" maxlength="9" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">JSHSHIR (PINFL)</label>
          <input v-model="personal.pinfl" class="input" maxlength="14" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Qo'shimcha telefon</label>
          <input v-model="personal.additional_phone" class="input" placeholder="+998..." />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
          <input v-model="personal.email" type="email" class="input" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Viloyat</label>
          <select v-model="personal.region_id" class="input">
            <option :value="null">— tanlang —</option>
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Tuman</label>
          <select v-model="personal.district_id" class="input" :disabled="!personal.region_id">
            <option :value="null">— tanlang —</option>
            <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Manzil</label>
          <input v-model="personal.address" class="input" placeholder="To'liq yashash manzili" />
        </div>
      </div>
      <button class="btn-primary" :disabled="saving" @click="savePersonal">
        <Save class="w-4 h-4" />
        {{ saving ? 'Saqlanmoqda...' : 'Saqlash' }}
      </button>
    </section>

    <section v-if="profile" class="card p-6">
      <h3 class="font-semibold text-slate-900 dark:text-slate-100 mb-2">Diplom</h3>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        Diplom (1-kurs) yoki perevod diplomi keyingi versiyada qo'shiladi.
      </p>
    </section>
  </div>
</template>
