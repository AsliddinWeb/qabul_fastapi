<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Save } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type BranchRead, type NamedRecord } from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()

const id = computed(() => route.params.id as string | undefined)
const isEdit = computed(() => !!id.value)
const toast = useToast()

interface FormState {
  branch_id: string
  education_level_id: string
  education_form_id: string
  name: string
  code: string
  tuition_fee: number | null
  study_duration_years: number
  contract_series: string
  is_active: boolean
}

const form = reactive<FormState>({
  branch_id: '',
  education_level_id: '',
  education_form_id: '',
  name: '',
  code: '',
  tuition_fee: null,
  study_duration_years: 4,
  contract_series: '',
  is_active: true,
})

// Display string with thousand separators (synced with form.tuition_fee)
const tuitionDisplay = ref('')

function formatNumber(n: number | null): string {
  if (n === null || isNaN(n)) return ''
  return n.toLocaleString('uz-UZ').replace(/,/g, ' ')
}

function parseNumber(s: string): number | null {
  const digits = s.replace(/\D/g, '')
  if (!digits) return null
  return parseInt(digits, 10)
}

function onTuitionInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value
  const num = parseNumber(raw)
  form.tuition_fee = num
  tuitionDisplay.value = num === null ? '' : formatNumber(num)
  validateField('tuition_fee')
}

const branches = ref<BranchRead[]>([])
const educationLevels = ref<NamedRecord[]>([])
const educationForms = ref<NamedRecord[]>([])
const saving = ref(false)
const loading = ref(false)
const errors = ref<Record<string, string>>({})

onMounted(async () => {
  loading.value = true
  try {
    const [b, l, f] = await Promise.all([
      adminApi.branches.list(false),
      adminApi.educationLevels.list(),
      adminApi.educationForms.list(),
    ])
    branches.value = b
    educationLevels.value = l
    educationForms.value = f

    if (isEdit.value && id.value) {
      const p = await adminApi.programs.get(id.value)
      Object.assign(form, {
        branch_id: p.branch_id,
        education_level_id: p.education_level_id,
        education_form_id: p.education_form_id,
        name: p.name,
        code: p.code,
        tuition_fee: typeof p.tuition_fee === 'string' ? parseNumber(p.tuition_fee) : p.tuition_fee,
        study_duration_years: (p as any).study_duration_years || 4,
        contract_series: p.contract_series,
        is_active: p.is_active,
      })
      tuitionDisplay.value = formatNumber(form.tuition_fee)
    }
  } finally {
    loading.value = false
  }
})

function validateField(field: string) {
  const ne = { ...errors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'branch_id':            err = form.branch_id ? null : "Filialni tanlang"; break
    case 'education_level_id':   err = form.education_level_id ? null : "Ta'lim darajasini tanlang"; break
    case 'education_form_id':    err = form.education_form_id ? null : "Ta'lim shaklini tanlang"; break
    case 'name':                 err = form.name.trim() ? null : "Yo'nalish nomini kiriting"; break
    case 'code':                 err = form.code.trim() ? null : "Kodni kiriting"; break
    case 'tuition_fee':          err = form.tuition_fee && form.tuition_fee > 0 ? null : "Yillik to'lov 0 dan katta bo'lishi kerak"; break
    case 'study_duration_years': err = (form.study_duration_years >= 1 && form.study_duration_years <= 8) ? null : "Muddati 1-8 yil oraligida"; break
    case 'contract_series':      err = form.contract_series.trim() ? null : "Shartnoma seriyasini kiriting"; break
  }
  if (err) ne[field] = err
  errors.value = ne
}

function validate(): boolean {
  ;['branch_id', 'education_level_id', 'education_form_id', 'name', 'code',
    'tuition_fee', 'study_duration_years', 'contract_series'].forEach(validateField)
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) {
    toast.error("Maydonlarni to'ldiring")
    return
  }
  saving.value = true
  try {
    const payload = {
      branch_id: form.branch_id,
      education_level_id: form.education_level_id,
      education_form_id: form.education_form_id,
      name: form.name.trim(),
      code: form.code.trim(),
      tuition_fee: form.tuition_fee,
      study_duration_years: form.study_duration_years,
      contract_series: form.contract_series.trim(),
      is_active: form.is_active,
    } as any
    if (isEdit.value && id.value) {
      await adminApi.programs.update(id.value, payload)
      toast.success("Yo'nalish yangilandi")
    } else {
      await adminApi.programs.create(payload)
      toast.success("Yo'nalish yaratildi")
    }
    router.push('/admin/programs')
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <PageHeader
      :title="isEdit ? `Yo'nalishni tahrirlash` : `Yangi yo'nalish`"
      subtitle="Filial · ta'lim darajasi · ta'lim shakli + nom · kod · narx"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: `Yo'nalishlar`, to: '/admin/programs' }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <Skeleton v-if="loading" type="form" />

    <form v-else class="card p-6 space-y-5" @submit.prevent="submit">
      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Filial *</label>
          <select v-model="form.branch_id" class="input"
                  :class="errors.branch_id ? 'border-red-500' : ''"
                  @blur="validateField('branch_id')">
            <option value="">— tanlang —</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
          <p v-if="errors.branch_id" class="mt-1 text-xs text-red-600">{{ errors.branch_id }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ta'lim darajasi *</label>
          <select v-model="form.education_level_id" class="input"
                  :class="errors.education_level_id ? 'border-red-500' : ''"
                  @blur="validateField('education_level_id')">
            <option value="">— tanlang —</option>
            <option v-for="l in educationLevels" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
          <p v-if="errors.education_level_id" class="mt-1 text-xs text-red-600">{{ errors.education_level_id }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ta'lim shakli *</label>
          <select v-model="form.education_form_id" class="input"
                  :class="errors.education_form_id ? 'border-red-500' : ''"
                  @blur="validateField('education_form_id')">
            <option value="">— tanlang —</option>
            <option v-for="f in educationForms" :key="f.id" :value="f.id">{{ f.name }}</option>
          </select>
          <p v-if="errors.education_form_id" class="mt-1 text-xs text-red-600">{{ errors.education_form_id }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yo'nalish kodi *</label>
          <input v-model="form.code" class="input font-mono"
                 :class="errors.code ? 'border-red-500' : ''"
                 placeholder="5330200"
                 @blur="validateField('code')" />
          <p v-if="errors.code" class="mt-1 text-xs text-red-600">{{ errors.code }}</p>
        </div>
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yo'nalish nomi *</label>
          <input v-model="form.name" class="input"
                 :class="errors.name ? 'border-red-500' : ''"
                 placeholder="Dasturiy injiniring"
                 @blur="validateField('name')" />
          <p v-if="errors.name" class="mt-1 text-xs text-red-600">{{ errors.name }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yillik to'lov (so'm) *</label>
          <div class="relative">
            <input :value="tuitionDisplay"
                   inputmode="numeric"
                   class="input font-mono pr-12"
                   :class="errors.tuition_fee ? 'border-red-500' : ''"
                   placeholder="15 000 000"
                   @input="onTuitionInput"
                   @blur="validateField('tuition_fee')" />
            <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 pointer-events-none">so'm</span>
          </div>
          <p v-if="errors.tuition_fee" class="mt-1 text-xs text-red-600">{{ errors.tuition_fee }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">O'qish muddati (yil) *</label>
          <select v-model.number="form.study_duration_years" class="input"
                  :class="errors.study_duration_years ? 'border-red-500' : ''">
            <option :value="1">1 yil</option>
            <option :value="2">2 yil</option>
            <option :value="3">3 yil</option>
            <option :value="4">4 yil</option>
            <option :value="5">5 yil</option>
            <option :value="6">6 yil</option>
          </select>
          <p v-if="errors.study_duration_years" class="mt-1 text-xs text-red-600">{{ errors.study_duration_years }}</p>
        </div>
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Shartnoma seriyasi *</label>
          <input v-model="form.contract_series" class="input font-mono"
                 :class="errors.contract_series ? 'border-red-500' : ''"
                 placeholder="2026-BK"
                 @blur="validateField('contract_series')" />
          <p v-if="errors.contract_series" class="mt-1 text-xs text-red-600">{{ errors.contract_series }}</p>
        </div>
        <label class="sm:col-span-2 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input v-model="form.is_active" type="checkbox" class="rounded" />
          <span>Faol holatda (abituriyentlarga ko'rinadi)</span>
        </label>
      </div>

      <div class="flex gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
        <button type="submit" class="btn-primary" :disabled="saving">
          <Save class="w-4 h-4" />
          {{ saving ? 'Saqlanmoqda...' : (isEdit ? 'Yangilash' : 'Yaratish') }}
        </button>
        <button type="button" class="btn-ghost" @click="router.push('/admin/programs')">Bekor qilish</button>
      </div>
    </form>
  </div>
</template>
