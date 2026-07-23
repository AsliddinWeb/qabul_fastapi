<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  ArrowLeft, Save, Shuffle, Phone, User as UserIcon,
  Send, ChevronDown, ChevronUp, AlertCircle, CheckCircle2,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { leadsApi, type LeadPipeline, type LeadStage, type LeadSource } from '@/api/leads.api'
import { adminApi } from '@/api/admin.api'
import { usersApi, type UserLookup } from '@/api/users.api'
import { useToast } from '@/composables/useToast'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { formatPhone, compactPhone, PLACEHOLDERS } from '@/utils/validators'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const toast = useToast()

const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')

const form = reactive({
  full_name: '',
  phone: '',
  telegram_username: '',
  source_id: '',
  pipeline_id: '',
  stage_id: '',
  branch_id: '',
  program_id: '',
  assigned_to_id: '',
  auto_assign: true,        // default: avto-biriktirish — operator vaqt sarflamasin
  notes: '',
})

const showAdvanced = ref(false)

const pipelines = ref<LeadPipeline[]>([])
const stages = ref<LeadStage[]>([])
const sources = ref<LeadSource[]>([])
const branches = ref<any[]>([])
const programs = ref<any[]>([])
// Lookup shape — id + full_name is all the assignee picker needs.
const operators = ref<UserLookup[]>([])

const saving = ref(false)
const loading = ref(true)
const errors = ref<Record<string, string>>({})
const touched = ref<Record<string, boolean>>({})

// === Real-time validation ===
function validatePhone(v: string): string | null {
  const digits = v.replace(/\D/g, '')
  if (!digits) return "Telefon majburiy"
  // Accept either "+998 + 9 digits" (12 digits total) or 9 digits (auto-prefixed)
  if (digits.length < 9) return "Telefon to'liq emas"
  if (digits.length === 12 && !digits.startsWith('998')) return "Format: +998 XX XXX XX XX"
  if (digits.length > 12) return "Telefon juda uzun"
  return null
}
function validateName(v: string): string | null {
  const trimmed = v.trim()
  if (!trimmed) return "F.I.Sh. majburiy"
  if (trimmed.length < 3) return "Kamida 3 belgi"
  // O'zbekcha ismlarda apostrof, ' va  - belgilar bo'lishi mumkin
  if (!/^[a-zA-Zа-яА-ЯёЁўЎқҚғҒҳҲ'`’\s\-]+$/u.test(trimmed)) return "Faqat harflar"
  return null
}
function validateTelegram(v: string): string | null {
  if (!v.trim()) return null  // ixtiyoriy
  const cleaned = v.trim().replace(/^@/, '')
  if (cleaned.length < 4) return "Kamida 4 belgi"
  if (!/^[a-zA-Z][a-zA-Z0-9_]{3,31}$/.test(cleaned)) return "Faqat lotin harf, raqam, _"
  return null
}

function recompute(field: string) {
  const e = { ...errors.value }
  delete e[field]
  let err: string | null = null
  if (field === 'full_name') err = validateName(form.full_name)
  if (field === 'phone') err = validatePhone(form.phone)
  if (field === 'telegram_username') err = validateTelegram(form.telegram_username)
  if (err) e[field] = err
  errors.value = e
}

watch(() => form.full_name, () => { if (touched.value.full_name) recompute('full_name') })
watch(() => form.phone, () => { if (touched.value.phone) recompute('phone') })
watch(() => form.telegram_username, () => { if (touched.value.telegram_username) recompute('telegram_username') })

function blur(field: string) {
  touched.value[field] = true
  recompute(field)
  if (field === 'phone') void checkPhoneDuplicate()
}

// Format phone as the user types: "+998 94 202 55 11" pattern.
function onPhoneInput(e: Event) {
  const el = e.target as HTMLInputElement
  form.phone = formatPhone(el.value)
  // User is mid-edit; clear any stale duplicate hint until they blur.
  if (duplicateHint.value) duplicateHint.value = null
}

// Pre-submit duplicate check — fires on phone blur.
interface DuplicateHint {
  lead_id: string
  full_name?: string | null
  assigned_to_name?: string | null
  stage_name?: string | null
}
const duplicateHint = ref<DuplicateHint | null>(null)
let dupeReqAbort: AbortController | null = null
async function checkPhoneDuplicate() {
  if (validatePhone(form.phone)) { duplicateHint.value = null; return }
  const compact = compactPhone(form.phone)
  if (dupeReqAbort) dupeReqAbort.abort()
  dupeReqAbort = new AbortController()
  try {
    const res = await leadsApi.checkPhone(compact)
    if (res.exists && res.lead_id) {
      duplicateHint.value = {
        lead_id: res.lead_id,
        full_name: res.full_name,
        assigned_to_name: res.assigned_to_name,
        stage_name: res.stage_name,
      }
    } else {
      duplicateHint.value = null
    }
  } catch { /* ignore — submit path will surface any real error */ }
}

// === Form valid? ===
const isValid = computed(() => {
  if (validateName(form.full_name)) return false
  if (validatePhone(form.phone)) return false
  if (validateTelegram(form.telegram_username)) return false
  return true
})

// === Catalog options ===
const pipelineOptions = computed(() => pipelines.value.map(p => ({ id: p.id, label: p.name })))
const stageOptions = computed(() =>
  form.pipeline_id ? stages.value.filter(s => s.pipeline_id === form.pipeline_id).map(s => ({ id: s.id, label: s.name })) : [],
)
const sourceOptions = computed(() => sources.value.map(s => ({ id: s.id, label: s.name })))
const branchOptions = computed(() => branches.value.map(b => ({ id: b.id, label: b.name })))
const programOptions = computed(() =>
  programs.value
    .filter(p => !form.branch_id || p.branch_id === form.branch_id)
    .map(p => ({ id: p.id, label: p.name, sub: p.code })),
)
const operatorOptions = computed(() => operators.value.map(u => ({
  id: u.id,
  label: u.full_name || u.phone || u.id.slice(0, 8),
  sub: u.phone || '',
})))

onMounted(async () => {
  try {
    const [pp, src, brs, prgs, ops] = await Promise.all([
      leadsApi.pipelines.list().catch(() => []),
      leadsApi.sources.list().catch(() => []),
      adminApi.branches.list(false).catch(() => []),
      adminApi.programs.list().catch(() => []),
      // Auth-only lookup so operators can pick the initial assignee too.
      usersApi.byRole('operator').catch(() => []),
    ])
    pipelines.value = pp
    sources.value = src
    branches.value = brs
    programs.value = prgs
    operators.value = ops
    const def = pp.find(p => p.is_default) || pp[0]
    if (def) form.pipeline_id = def.id
    // Operator panel: lead is auto-assigned to the current operator
    if (isOperatorPanel.value && auth.user?.id) {
      form.assigned_to_id = auth.user.id
      form.auto_assign = false
    }
  } finally {
    loading.value = false
  }
})

watch(() => form.pipeline_id, async (v) => {
  form.stage_id = ''
  stages.value = v ? await leadsApi.stages.list(v).catch(() => []) : []
})

watch(() => form.branch_id, () => {
  if (form.program_id && !programOptions.value.some(o => o.id === form.program_id)) form.program_id = ''
})

watch(() => form.assigned_to_id, (v) => {
  if (v) form.auto_assign = false
})

async function submit() {
  // Force-validate everything
  ;['full_name', 'phone', 'telegram_username'].forEach((f) => { touched.value[f] = true; recompute(f) })
  if (!isValid.value) {
    toast.error("Maydonlarni to'ldiring")
    return
  }
  saving.value = true
  try {
    const res = await leadsApi.create({
      full_name: form.full_name.trim(),
      phone: compactPhone(form.phone),
      telegram_username: form.telegram_username.trim().replace(/^@/, '') || null,
      pipeline_id: form.pipeline_id || null,
      stage_id: form.stage_id || null,
      source_id: form.source_id || null,
      branch_id: form.branch_id || null,
      program_id: form.program_id || null,
      assigned_to_id: form.assigned_to_id || null,
      auto_assign: form.auto_assign,
      notes: form.notes.trim() || null,
    })
    toast.success("Lead yaratildi")
    router.push(`${panelPrefix.value}/leads/${res.lead.id}`)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { code?: string; message?: string; details?: DuplicateHint }; detail?: string }>
    const err = ax.response?.data?.error
    // Duplicate phone: backend refuses to create/merge. Surface the existing
    // lead as a link instead of silently pulling it into this operator's funnel.
    if (ax.response?.status === 409 && err?.code === "lead_duplicate_phone" && err.details?.lead_id) {
      duplicateHint.value = {
        lead_id: err.details.lead_id,
        full_name: err.details.full_name,
        assigned_to_name: err.details.assigned_to_name,
        stage_name: err.details.stage_name,
      }
      toast.error("Bu telefon allaqachon ro'yxatda — mavjud lead'ni oching")
    } else {
      toast.error(err?.message || ax.response?.data?.detail || "Xatolik")
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-5">
    <PageHeader
      title="Yangi lead"
      subtitle="Faqat F.I.Sh. va telefon majburiy. Qolgani ixtiyoriy."
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'CRM', to: `${panelPrefix}/leads` }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <Skeleton v-if="loading" type="form" :rows="6" />

    <form v-else class="card p-6 space-y-5" @submit.prevent="submit">
      <div class="grid sm:grid-cols-2 gap-4">
        <!-- F.I.Sh. -->
        <div>
          <label class="field-label inline-flex items-center gap-1">
            <UserIcon class="w-3 h-3" /> F.I.Sh. <span class="text-rose-500">*</span>
          </label>
          <input v-model="form.full_name"
                 class="input"
                 :class="errors.full_name ? '!border-rose-400 focus:!ring-rose-200' : ''"
                 placeholder="Valiyev Ali"
                 autocomplete="off"
                 @blur="blur('full_name')" />
          <p v-if="errors.full_name" class="mt-1 text-xs text-rose-600 inline-flex items-center gap-1">
            <AlertCircle class="w-3 h-3" /> {{ errors.full_name }}
          </p>
        </div>

        <!-- Telefon -->
        <div>
          <label class="field-label inline-flex items-center gap-1">
            <Phone class="w-3 h-3" /> Telefon <span class="text-rose-500">*</span>
          </label>
          <input :value="form.phone"
                 class="input font-mono"
                 :class="errors.phone ? '!border-rose-400 focus:!ring-rose-200' : ''"
                 :placeholder="PLACEHOLDERS.phoneUz"
                 inputmode="tel"
                 autocomplete="off"
                 @input="onPhoneInput"
                 @blur="blur('phone')" />
          <p v-if="errors.phone" class="mt-1 text-xs text-rose-600 inline-flex items-center gap-1">
            <AlertCircle class="w-3 h-3" /> {{ errors.phone }}
          </p>
          <p v-else-if="touched.phone && form.phone && !duplicateHint"
             class="mt-1 text-xs text-emerald-600 inline-flex items-center gap-1">
            <CheckCircle2 class="w-3 h-3" /> Yaxshi
          </p>

          <!-- Duplicate hint — backend already merges silently, this just
               warns the operator before submit so they know they're
               touching an existing record (possibly someone else's). -->
          <div v-if="duplicateHint"
               class="mt-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-500/10 ring-1 ring-amber-200 dark:ring-amber-500/30 text-amber-900 dark:text-amber-200 text-xs">
            <div class="flex items-start gap-2">
              <AlertCircle class="w-4 h-4 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
              <div class="flex-1 min-w-0">
                <div class="font-semibold mb-0.5">Bu telefon allaqachon ro'yxatda</div>
                <div class="leading-relaxed text-amber-800 dark:text-amber-300">
                  <span v-if="duplicateHint.full_name" class="font-medium">{{ duplicateHint.full_name }}</span>
                  <template v-if="duplicateHint.assigned_to_name">
                    · {{ duplicateHint.assigned_to_name }} operatorga biriktirilgan
                  </template>
                  <template v-else>· operator biriktirilmagan</template>
                  <span v-if="duplicateHint.stage_name" class="text-amber-700 dark:text-amber-400/80"> · {{ duplicateHint.stage_name }}</span>
                </div>
                <RouterLink :to="`${panelPrefix}/leads/${duplicateHint.lead_id}`"
                            class="inline-flex items-center gap-1 mt-1.5 font-semibold text-amber-900 dark:text-amber-200 hover:underline">
                  Mavjud lead'ni ko'rish →
                </RouterLink>
              </div>
            </div>
          </div>
        </div>

        <!-- Telegram -->
        <div>
          <label class="field-label inline-flex items-center gap-1">
            <Send class="w-3 h-3" /> Telegram username
          </label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-mono pointer-events-none">@</span>
            <input v-model="form.telegram_username"
                   class="input pl-7 font-mono"
                   :class="errors.telegram_username ? '!border-rose-400 focus:!ring-rose-200' : ''"
                   placeholder="username"
                   autocomplete="off"
                   @blur="blur('telegram_username')" />
          </div>
          <p v-if="errors.telegram_username" class="mt-1 text-xs text-rose-600 inline-flex items-center gap-1">
            <AlertCircle class="w-3 h-3" /> {{ errors.telegram_username }}
          </p>
          <p v-else class="field-hint">Aloqa uchun ikkinchi yo'l. Ixtiyoriy.</p>
        </div>

        <!-- Manba -->
        <div>
          <label class="field-label">Manba</label>
          <SearchSelect v-model="form.source_id" :options="sourceOptions" placeholder="— tanlang —" allow-clear />
        </div>
      </div>

      <!-- Operator (admin only — operator panel auto-assigns to self) -->
      <div v-if="isOperatorPanel" class="rounded-xl bg-emerald-50 dark:bg-emerald-500/10 ring-1 ring-emerald-200/60 dark:ring-emerald-700/30 p-3 text-sm text-emerald-800 dark:text-emerald-300 inline-flex items-center gap-2">
        <CheckCircle2 class="w-4 h-4 shrink-0" />
        Bu lead avtomatik <strong>sizga</strong> biriktiriladi.
      </div>
      <div v-else class="rounded-xl bg-slate-50 dark:bg-slate-800/40 ring-1 ring-slate-200/60 dark:ring-slate-700/40 p-3">
        <label class="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" v-model="form.auto_assign" class="rounded" />
          <Shuffle class="w-3.5 h-3.5 text-slate-500" />
          <span class="text-slate-700 dark:text-slate-300">Operatorga avtomatik biriktirish (kam yuklamali)</span>
        </label>
        <div v-if="!form.auto_assign" class="mt-2.5">
          <SearchSelect v-model="form.assigned_to_id" :options="operatorOptions" placeholder="— operatorni tanlang —" allow-clear />
        </div>
      </div>

      <!-- Advanced (toggle) -->
      <div>
        <button type="button"
                class="text-xs font-semibold text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 uppercase tracking-wider inline-flex items-center gap-1"
                @click="showAdvanced = !showAdvanced">
          <component :is="showAdvanced ? ChevronUp : ChevronDown" class="w-3 h-3" />
          Qo'shimcha {{ showAdvanced ? '' : '(varonka, yo\'nalish, eslatma)' }}
        </button>

        <div v-show="showAdvanced" class="mt-4 space-y-4 pl-3 border-l-2 border-slate-200 dark:border-slate-800">
          <div class="grid sm:grid-cols-2 gap-3">
            <div>
              <label class="field-label">Varonka</label>
              <SearchSelect v-model="form.pipeline_id" :options="pipelineOptions" placeholder="— default —" />
            </div>
            <div>
              <label class="field-label">Boshlang'ich bosqich</label>
              <SearchSelect v-model="form.stage_id" :options="stageOptions" placeholder="— birinchi —" allow-clear :disabled="!form.pipeline_id" />
            </div>
            <div>
              <label class="field-label">Filial</label>
              <SearchSelect v-model="form.branch_id" :options="branchOptions" placeholder="— tanlang —" allow-clear />
            </div>
            <div>
              <label class="field-label">Yo'nalish</label>
              <SearchSelect v-model="form.program_id" :options="programOptions" placeholder="— tanlang —" allow-clear :disabled="!form.branch_id" />
            </div>
          </div>
          <div>
            <label class="field-label">Eslatma</label>
            <textarea v-model="form.notes" class="input" rows="3" placeholder="Lead haqida muhim ma'lumotlar"></textarea>
          </div>
        </div>
      </div>

      <!-- Submit -->
      <div class="flex items-center justify-between gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
        <RouterLink :to="`${panelPrefix}/leads`" class="text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100">Bekor</RouterLink>
        <button type="submit" class="btn-primary" :disabled="saving || !isValid || !!duplicateHint">
          <Save class="w-4 h-4" /> {{ saving ? 'Saqlanmoqda...' : 'Lead yaratish' }}
        </button>
      </div>
    </form>
  </div>
</template>
