<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import { contractsApi, type ContractCreatePayload, type ContractTemplateRead } from '@/api/contracts.api'
import { staffApi } from '@/api/staff.api'
import type { ApplicationDetailed } from '@/api/applications.api'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()

const applicationId = computed(() => route.query.application as string)

const application = ref<ApplicationDetailed | null>(null)
const templates = ref<ContractTemplateRead[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)

const form = reactive<ContractCreatePayload>({
  application_id: '',
  template_id: '',
  type: 'two_party',
  total_amount: null,
  currency: 'UZS',
  additional_party: null,
})

const additionalParty = reactive({
  party_role: 'sponsor' as 'sponsor' | 'parent',
  full_name: '',
  pinfl: '',
  passport_series: '',
  passport_number: '',
  phone: '',
  relationship: '',
  address: '',
})

onMounted(async () => {
  if (!applicationId.value) {
    error.value = "Application ID kerak"
    loading.value = false
    return
  }
  try {
    const [app, tpls] = await Promise.all([
      staffApi.applications.get(applicationId.value),
      contractsApi.templates(),
    ])
    application.value = app
    templates.value = tpls
    form.application_id = app.id
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    error.value = ax.response?.data?.error?.message || 'Ma\'lumotlarni yuklab bo\'lmadi'
  } finally {
    loading.value = false
  }
})

// Filter templates: any active template that has a body for the selected type.
const compatibleTemplates = computed(() =>
  templates.value.filter((t) => {
    if (!t.is_active) return false
    return form.type === 'three_party' ? !!t.body_three_party : !!t.body_two_party
  }),
)

// Reset template when type changes
watch(() => form.type, () => { form.template_id = '' })

async function submit() {
  error.value = null
  if (!form.template_id) {
    error.value = 'Shablon tanlang'
    return
  }

  saving.value = true
  try {
    const payload: ContractCreatePayload = {
      application_id: form.application_id,
      template_id: form.template_id,
      type: form.type,
      currency: form.currency || 'UZS',
      total_amount: form.total_amount || null,
    }
    if (form.type === 'three_party') {
      if (!additionalParty.full_name) {
        error.value = "Uchinchi tomon ma'lumotlari to'liq emas"
        saving.value = false
        return
      }
      payload.additional_party = { ...additionalParty }
    }

    const created = await contractsApi.create(payload)
    router.push(`/operator/contracts/${created.id}`)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    error.value = ax.response?.data?.error?.message || "Yaratib bo'lmadi"
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <PageHeader
      title="Shartnoma yaratish"
      subtitle="Ariza qabul qilingach shu yerdan shartnoma rasmiylashtiriladi"
      :crumbs="[{ label: 'Bosh sahifa' }, { label: 'Shartnomalar' }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">‹ Ortga</button>
    </PageHeader>

    <div v-if="error" class="text-sm rounded-lg p-3 bg-red-50 text-red-700">{{ error }}</div>

    <Skeleton v-if="loading" type="form" />

    <form v-else-if="application" class="card p-6 space-y-5" @submit.prevent="submit">
      <div class="bg-slate-50 p-3 rounded-lg text-sm">
        <div><strong>Ariza:</strong> {{ application.application_number }}</div>
        <div class="text-slate-600">{{ application.program_name }} ({{ application.branch_name }})</div>
      </div>

      <div>
        <label class="block text-sm font-medium mb-1">Shartnoma turi *</label>
        <div class="flex gap-3">
          <label class="flex items-center gap-2">
            <input v-model="form.type" type="radio" value="two_party" />
            <span>2 tomonlama (Universitet + Talaba)</span>
          </label>
          <label class="flex items-center gap-2">
            <input v-model="form.type" type="radio" value="three_party" />
            <span>3 tomonlama (+ sponsor/ota-ona)</span>
          </label>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium mb-1">Shablon *</label>
        <select v-model="form.template_id" class="input">
          <option value="">— tanlang —</option>
          <option v-for="t in compatibleTemplates" :key="t.id" :value="t.id">
            {{ t.name }} (v{{ t.version }})
          </option>
        </select>
        <p v-if="!compatibleTemplates.length" class="mt-1 text-xs text-amber-600">
          Bu turdagi shablon yo'q. Avval admin paneldan shablon yarating yoki
          <code>make seed-templates</code> ishga tushiring.
        </p>
      </div>

      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Jami summa (so'mda)</label>
          <input v-model="form.total_amount" type="number" step="0.01" class="input"
                 placeholder="Bo'sh bo'lsa offering tuition_fee qo'llanadi" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Valyuta</label>
          <input v-model="form.currency" class="input" maxlength="3" />
        </div>
      </div>

      <!-- Additional party -->
      <fieldset v-if="form.type === 'three_party'" class="border border-slate-200 rounded-lg p-4 space-y-3">
        <legend class="px-2 text-sm font-medium">Uchinchi tomon</legend>
        <div class="grid sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium mb-1">Rol</label>
            <select v-model="additionalParty.party_role" class="input">
              <option value="sponsor">Sponsor (tashkilot)</option>
              <option value="parent">Ota-ona</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">F.I.O. *</label>
            <input v-model="additionalParty.full_name" class="input" />
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">JSHSHIR</label>
            <input v-model="additionalParty.pinfl" class="input" maxlength="14" />
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">Telefon</label>
            <input v-model="additionalParty.phone" class="input" />
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">Pasport seriya</label>
            <input v-model="additionalParty.passport_series" class="input uppercase" maxlength="2" />
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">Pasport raqam</label>
            <input v-model="additionalParty.passport_number" class="input" maxlength="7" />
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">Munosabat</label>
            <input v-model="additionalParty.relationship" class="input" placeholder="ota / ona / tashkilot" />
          </div>
          <div class="sm:col-span-2">
            <label class="block text-xs font-medium mb-1">Manzil</label>
            <input v-model="additionalParty.address" class="input" />
          </div>
        </div>
      </fieldset>

      <div class="flex gap-3 pt-2">
        <button type="submit" class="btn-primary" :disabled="saving">
          {{ saving ? 'Yaratilmoqda...' : 'Shartnoma yaratish' }}
        </button>
        <button type="button" class="btn-ghost" @click="router.back()">Bekor qilish</button>
      </div>
    </form>
  </div>
</template>
