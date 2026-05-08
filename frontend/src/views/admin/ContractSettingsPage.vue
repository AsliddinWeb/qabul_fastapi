<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Building2, Save, Hash, MapPin, User as UserIcon, Briefcase, FileText } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { contractsApi, type ContractSettings, type ContractSettingsUpdatePayload } from '@/api/contracts.api'
import { useToast } from '@/composables/useToast'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const toast = useToast()

const loading = ref(true)
const saving = ref(false)
const settings = ref<ContractSettings | null>(null)

const form = reactive<ContractSettingsUpdatePayload>({
  company_name: '',
  company_address: '',
  company_inn: '',
  director_name: '',
  director_title: 'Rektor',
  default_contract_type: 'two_party',
  auto_generate_pdf: true,
  pdf_page_size: 'A4',
})

onMounted(async () => {
  loading.value = true
  try {
    const s = await contractsApi.getSettings()
    settings.value = s
    Object.assign(form, {
      company_name: s.company_name || '',
      company_address: s.company_address || '',
      company_inn: s.company_inn || '',
      director_name: s.director_name || '',
      director_title: s.director_title || 'Rektor',
      default_contract_type: s.default_contract_type,
      auto_generate_pdf: s.auto_generate_pdf,
      pdf_page_size: s.pdf_page_size,
    })
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Sozlamalarni yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
})

async function save() {
  if (!form.company_name || !form.company_name.trim()) {
    toast.error("Universitet nomi bo'sh bo'la olmaydi")
    return
  }
  saving.value = true
  try {
    const updated = await contractsApi.updateSettings({
      company_name: form.company_name?.trim(),
      company_address: form.company_address?.trim() || null,
      company_inn: form.company_inn?.trim() || null,
      director_name: form.director_name?.trim() || null,
      director_title: form.director_title?.trim() || 'Rektor',
      default_contract_type: form.default_contract_type,
      auto_generate_pdf: form.auto_generate_pdf,
      pdf_page_size: form.pdf_page_size,
    })
    settings.value = updated
    toast.success('Saqlandi')
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <PageHeader
      title="Shartnoma sozlamalari"
      subtitle="Universitet rekvizitlari (kontrakt PDF'larida ishlatiladi) va shartnoma generatsiyasi parametrlari"
    />

    <!-- Loading skeleton -->
    <div v-if="loading" class="card p-6">
      <Skeleton class="h-7 w-1/3 mb-4" />
      <Skeleton v-for="i in 5" :key="i" class="h-12 mb-3" />
    </div>

    <form v-else class="space-y-5" @submit.prevent="save">
      <!-- Universitet rekvizitlari -->
      <section class="card p-5 sm:p-6">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-1 inline-flex items-center gap-2">
          <Building2 class="w-4 h-4 text-indigo-500" />
          Universitet rekvizitlari
        </h2>
        <p class="text-xs text-slate-500 dark:text-slate-400 mb-5">
          Bu maydonlar yangi shartnomalar PDF'ida "tomon" sifatida chiqadi
        </p>

        <div class="grid sm:grid-cols-2 gap-4">
          <div class="sm:col-span-2">
            <label class="label inline-flex items-center gap-1.5">
              <Building2 class="w-3 h-3" /> Nomi <span class="text-rose-500">*</span>
            </label>
            <input v-model="form.company_name" class="input" placeholder="Xalqaro Innovatsion Universiteti" />
          </div>

          <div class="sm:col-span-2">
            <label class="label inline-flex items-center gap-1.5">
              <MapPin class="w-3 h-3" /> Yuridik manzil
            </label>
            <input v-model="form.company_address" class="input"
                   placeholder="Qarshi shahri, I.Karimov ko'chasi 405-uy" />
          </div>

          <div>
            <label class="label inline-flex items-center gap-1.5">
              <Hash class="w-3 h-3" /> INN
            </label>
            <input v-model="form.company_inn" class="input font-mono" placeholder="123456789" maxlength="20" />
          </div>

          <div>
            <label class="label inline-flex items-center gap-1.5">
              <Briefcase class="w-3 h-3" /> Direktor lavozimi
            </label>
            <input v-model="form.director_title" class="input" placeholder="Rektor" />
          </div>

          <div class="sm:col-span-2">
            <label class="label inline-flex items-center gap-1.5">
              <UserIcon class="w-3 h-3" /> Direktor F.I.Sh.
            </label>
            <input v-model="form.director_name" class="input" placeholder="Aliyev Vali Aliyevich" />
          </div>
        </div>
      </section>

      <!-- Generatsiya parametrlari -->
      <section class="card p-5 sm:p-6">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-5 inline-flex items-center gap-2">
          <FileText class="w-4 h-4 text-violet-500" />
          PDF generatsiyasi
        </h2>

        <div class="grid sm:grid-cols-2 gap-4">
          <div>
            <label class="label">Standart shartnoma turi</label>
            <select v-model="form.default_contract_type" class="input">
              <option value="two_party">Ikki tomonlama</option>
              <option value="three_party">Uch tomonlama</option>
            </select>
          </div>

          <div>
            <label class="label">PDF qog'oz o'lchami</label>
            <select v-model="form.pdf_page_size" class="input">
              <option value="A4">A4</option>
              <option value="A5">A5</option>
              <option value="Letter">Letter</option>
            </select>
          </div>

          <label class="sm:col-span-2 flex items-center gap-2.5 cursor-pointer">
            <input v-model="form.auto_generate_pdf" type="checkbox" class="w-4 h-4 rounded" />
            <span class="text-sm text-slate-700 dark:text-slate-300">
              Shartnoma yaratilganda PDF ham avtomatik generatsiya qilinsin
            </span>
          </label>
        </div>
      </section>

      <!-- Save -->
      <div class="flex justify-end">
        <button
          type="submit"
          class="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold shadow disabled:opacity-50"
          :disabled="saving"
        >
          <Save class="w-4 h-4" />
          {{ saving ? 'Saqlanmoqda...' : 'Saqlash' }}
        </button>
      </div>
    </form>
  </div>
</template>
