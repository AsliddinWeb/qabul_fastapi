<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Phone, Mail, MessageCircle, CheckCircle2, XCircle,
  RotateCcw, Send, ArrowRight, User as UserIcon, Activity, Clock,
  Trash2, ChevronRight, Pencil, FileText, ExternalLink,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import {
  leadsApi, type Lead, type LeadActivity, type LeadStage, type LeadLostReason, type LeadSource,
} from '@/api/leads.api'
import { adminApi, type UserRead } from '@/api/admin.api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Skeleton from '@/components/ui/Skeleton.vue'
import { formatPhone, compactPhone, PLACEHOLDERS } from '@/utils/validators'
import SearchSelect from '@/components/ui/SearchSelect.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { ask } = useConfirm()

const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')
const isOperatorPanel = computed(() => panelPrefix.value === '/operator')

const id = computed(() => route.params.id as string)
const lead = ref<Lead | null>(null)

// Prev/next navigation: pulled from sessionStorage stash that LeadsListPage
// writes when its filtered list loads. If the user landed here from a
// bookmark / direct URL the stash is missing and the buttons stay hidden.
const navIds = computed<string[]>(() => {
  try {
    const raw = sessionStorage.getItem(`leadList:${panelPrefix.value}:ids`)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
})
const navIndex = computed(() => navIds.value.indexOf(id.value))
const prevLeadId = computed(() =>
  navIndex.value > 0 ? navIds.value[navIndex.value - 1] : null,
)
const nextLeadId = computed(() =>
  navIndex.value >= 0 && navIndex.value < navIds.value.length - 1
    ? navIds.value[navIndex.value + 1] : null,
)
function gotoSibling(leadId: string | null) {
  if (!leadId) return
  router.push(`${panelPrefix.value}/leads/${leadId}`)
}
const activities = ref<LeadActivity[]>([])
const stages = ref<LeadStage[]>([])
const lostReasons = ref<LeadLostReason[]>([])
const operators = ref<UserRead[]>([])
const sources = ref<LeadSource[]>([])
const branches = ref<any[]>([])
const programs = ref<any[]>([])
const loading = ref(true)
const newComment = ref('')
const sending = ref(false)

interface RelatedApp {
  id: string
  application_number: string
  status: string | null
  admission_type: string | null
  program_name: string | null
  branch_name: string | null
  created_at: string | null
  submitted_at: string | null
}
const relatedApps = ref<RelatedApp[]>([])

async function loadAll() {
  loading.value = true
  try {
    const l = await leadsApi.get(id.value)
    lead.value = l
    const [acts, sts, reasons, ops, srcs, brs, prgs, related] = await Promise.all([
      leadsApi.activities(id.value),
      leadsApi.stages.list(l.pipeline_id),
      leadsApi.lostReasons.list().catch(() => []),
      adminApi.users.list({ role: 'operator' as any, page: 1, size: 100 }).then(r => r.items).catch(() => []),
      leadsApi.sources.list().catch(() => []),
      adminApi.branches.list(false).catch(() => []),
      adminApi.programs.list().catch(() => []),
      leadsApi.relatedApplications(id.value).catch(() => ({ user_id: null, applications: [] as RelatedApp[] })),
    ])
    activities.value = acts
    stages.value = sts
    lostReasons.value = reasons
    operators.value = ops
    sources.value = srcs
    branches.value = brs
    programs.value = prgs
    relatedApps.value = related.applications
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
// Route-only navigation (Prev/Next changes :id but Vue reuses the
// component) needs a manual reload — otherwise the URL updates but the
// page keeps showing the previous lead.
watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) loadAll()
})

const stageOptions = computed(() => stages.value.map(s => ({ id: s.id, label: s.name })))
const operatorOptions = computed(() => operators.value.map(u => ({ id: u.id, label: u.full_name || u.phone })))
const reasonOptions = computed(() => lostReasons.value.map(r => ({ id: r.id, label: r.name })))
const sourceOptions = computed(() => sources.value.map(s => ({ id: s.id, label: s.name })))
const branchOptions = computed(() => branches.value.map(b => ({ id: b.id, label: b.name })))
const programOptions = computed(() =>
  programs.value
    .filter(p => !editForm.branch_id || p.branch_id === editForm.branch_id)
    .map(p => ({ id: p.id, label: p.name, sub: p.code })),
)

// === Inline edit ===
const editMode = ref(false)
const saving = ref(false)
const editForm = reactive({
  full_name: '',
  phone: '',
  telegram_username: '',
  source_id: '',
  branch_id: '',
  program_id: '',
  notes: '',
})

function enterEditMode() {
  if (!lead.value) return
  editForm.full_name = lead.value.full_name
  editForm.phone = formatPhone(lead.value.phone)
  editForm.telegram_username = lead.value.telegram_username || ''
  editForm.source_id = lead.value.source_id || ''
  editForm.branch_id = lead.value.branch_id || ''
  editForm.program_id = lead.value.program_id || ''
  editForm.notes = lead.value.notes || ''
  editMode.value = true
}

function cancelEdit() {
  editMode.value = false
}

async function saveEdit() {
  if (!editForm.full_name.trim()) { toast.error("F.I.Sh. majburiy"); return }
  if (!editForm.phone.trim()) { toast.error("Telefon majburiy"); return }
  saving.value = true
  try {
    await leadsApi.update(id.value, {
      full_name: editForm.full_name.trim(),
      phone: compactPhone(editForm.phone),
      telegram_username: editForm.telegram_username.trim().replace(/^@/, '') || null,
      source_id: editForm.source_id || null,
      branch_id: editForm.branch_id || null,
      program_id: editForm.program_id || null,
      notes: editForm.notes.trim() || null,
    } as any)
    toast.success("Saqlandi")
    editMode.value = false
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  } finally {
    saving.value = false
  }
}

const currentStage = computed(() => stages.value.find(s => s.id === lead.value?.stage_id))
const nextStage = computed(() => {
  if (!currentStage.value) return null
  const idx = stages.value.findIndex(s => s.id === currentStage.value!.id)
  return idx >= 0 && idx < stages.value.length - 1 ? stages.value[idx + 1] : null
})
const isTerminal = computed(() => !!currentStage.value?.is_terminal)

async function moveTo(stageId: string, comment?: string) {
  try {
    await leadsApi.move(id.value, stageId, comment)
    toast.success("Bosqich o'zgartirildi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

async function moveToNext() {
  if (nextStage.value) await moveTo(nextStage.value.id)
}

async function changeAssignee(user_id: string | null) {
  try {
    await leadsApi.assign(id.value, { user_id })
    toast.success("Operator o'zgartirildi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

async function autoAssign() {
  try {
    await leadsApi.assign(id.value, { auto_assign: true })
    toast.success("Avto-biriktirildi")
    await loadAll()
  } catch { toast.error("Xatolik") }
}

async function addComment() {
  if (!newComment.value.trim()) return
  sending.value = true
  try {
    await leadsApi.comment(id.value, newComment.value.trim())
    newComment.value = ''
    await loadAll()
  } catch { toast.error("Xatolik") }
  finally { sending.value = false }
}

const loggingCall = ref(false)
async function logCall() {
  loggingCall.value = true
  try {
    await leadsApi.logCall(id.value, newComment.value.trim() || undefined)
    newComment.value = ''
    toast.success("Qo'ng'iroq qayd etildi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  } finally {
    loggingCall.value = false
  }
}

const showLose = ref(false)
const loseForm = ref({ reason_id: '', comment: '' })
async function loseLead() {
  try {
    await leadsApi.lose(id.value, {
      reason_id: loseForm.value.reason_id || null,
      comment: loseForm.value.comment.trim() || undefined,
    })
    toast.success("Lead yo'qotilgan deb belgilandi")
    showLose.value = false
    loseForm.value = { reason_id: '', comment: '' }
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

// === Schedule next contact ===
const showSchedule = ref(false)
const scheduleForm = reactive({ next_contact_at: '', note: '' })

function openScheduleForm() {
  if (!lead.value) return
  // Default: now + 1 day at 10:00
  if (lead.value.next_contact_at) {
    scheduleForm.next_contact_at = lead.value.next_contact_at.slice(0, 16)
  } else {
    const d = new Date()
    d.setDate(d.getDate() + 1)
    d.setHours(10, 0, 0, 0)
    scheduleForm.next_contact_at = toLocalInput(d)
  }
  scheduleForm.note = lead.value.next_contact_note || ''
  showSchedule.value = true
}

function toLocalInput(d: Date): string {
  // datetime-local expects "YYYY-MM-DDTHH:mm" in local time
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function saveSchedule() {
  if (!scheduleForm.next_contact_at) {
    toast.error("Sana va vaqtni tanlang")
    return
  }
  try {
    const iso = new Date(scheduleForm.next_contact_at).toISOString()
    await leadsApi.schedule(id.value, {
      next_contact_at: iso,
      note: scheduleForm.note.trim() || null,
    })
    toast.success("Eslatma o'rnatildi")
    showSchedule.value = false
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

async function clearSchedule() {
  try {
    await leadsApi.schedule(id.value, { next_contact_at: null })
    toast.success("Eslatma o'chirildi")
    await loadAll()
  } catch { toast.error("Xatolik") }
}

const scheduleStatus = computed<'overdue' | 'today' | 'soon' | 'later' | 'none'>(() => {
  if (!lead.value?.next_contact_at) return 'none'
  const ts = new Date(lead.value.next_contact_at).getTime()
  const now = Date.now()
  const diff = ts - now
  if (diff < 0) return 'overdue'
  if (diff < 24 * 3_600_000) return 'today'
  if (diff < 3 * 24 * 3_600_000) return 'soon'
  return 'later'
})

function fmtSchedule(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('uz-UZ', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

async function reopen() {
  try {
    await leadsApi.reopen(id.value)
    toast.success("Lead qayta ochildi")
    await loadAll()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

async function convertToApplication() {
  if (!lead.value) return
  // Confirm and route to application form prefilled with lead_id
  const ok = await ask({
    title: "Arizaga o'tkazish",
    message: `${lead.value.full_name} uchun ariza yaratiladi. Davom etamizmi?`,
    confirmLabel: "Davom etish",
    tone: 'primary',
  })
  if (!ok) return
  router.push({ path: `${panelPrefix.value}/applications/new`, query: { lead_id: id.value } })
}

async function deleteLead() {
  const ok = await ask({
    title: "Lead'ni o'chirish",
    message: "Bu amalni qaytarib bo'lmaydi. Davom etamizmi?",
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await leadsApi.delete(id.value)
    toast.success("O'chirildi")
    router.push(`${panelPrefix.value}/leads`)
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}

const ACTION_LABELS: Record<string, string> = {
  create: 'Lead yaratildi',
  stage_move: 'Bosqich o\'zgartirildi',
  assign: 'Operator o\'zgartirildi',
  comment: 'Izoh qoldirildi',
  call: 'Qo\'ng\'iroq',
  merge: 'Boshqa lead bilan birlashtirildi',
  convert: 'Arizaga o\'tkazildi',
  lose: 'Yo\'qotildi',
  reopen: 'Qayta ochildi',
  update: 'Tahrirlandi',
  sla_alert: 'SLA ogohlantirish — bosqichda harakatsiz',
  schedule: 'Keyingi aloqa rejalashtirildi',
  schedule_clear: "Keyingi aloqa eslatmasi o'chirildi",
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function statusPill(s: string): string {
  return s === 'open' ? 'bg-brand-50 text-brand-700 ring-brand-200 dark:bg-brand-500/15 dark:text-brand-300'
    : s === 'won' ? 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300'
    : 'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-900/30 dark:text-rose-300'
}
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="lead" class="space-y-5">
    <div class="flex items-center justify-between gap-2 flex-wrap">
      <button class="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100"
              @click="router.push(`${panelPrefix}/leads`)">
        <ArrowLeft class="w-4 h-4" /> Lead'lar
      </button>
      <!-- Prev / next within the same filtered list. Hidden when we have
           no navigation context (direct URL access). -->
      <div v-if="navIndex >= 0" class="inline-flex items-center gap-1">
        <button type="button"
                class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
                :disabled="!prevLeadId"
                @click="gotoSibling(prevLeadId)">
          <ArrowLeft class="w-3 h-3" /> Oldingi
        </button>
        <span class="px-2 text-[11px] text-slate-500 dark:text-slate-400 tabular-nums">
          {{ navIndex + 1 }} / {{ navIds.length }}
        </span>
        <button type="button"
                class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
                :disabled="!nextLeadId"
                @click="gotoSibling(nextLeadId)">
          Keyingi <span aria-hidden="true">→</span>
        </button>
      </div>
    </div>

    <!-- Hero — bigger, cleaner -->
    <section class="card overflow-hidden">
      <div class="p-4 sm:p-7">
        <div class="flex flex-wrap items-start justify-between gap-5">
          <div class="flex items-start gap-3 sm:gap-5 min-w-0">
            <div class="grid place-items-center w-14 h-14 sm:w-20 sm:h-20 rounded-xl sm:rounded-2xl bg-brand-600 text-white text-lg sm:text-2xl font-bold shadow-md shrink-0">
              {{ (lead.full_name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()) }}
            </div>
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-1.5">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-full text-[11px] sm:text-xs font-semibold ring-1" :class="statusPill(lead.status)">
                  <span class="w-1.5 h-1.5 rounded-full"
                        :class="lead.status === 'open' ? 'bg-brand-500' : lead.status === 'won' ? 'bg-emerald-500' : 'bg-rose-500'"></span>
                  {{ lead.status === 'open' ? 'Faol lead' : lead.status === 'won' ? "Konversiya bo'lgan" : "Yo'qotilgan" }}
                </span>
                <span v-if="lead.pipeline_name" class="pill">{{ lead.pipeline_name }}</span>
                <span v-if="lead.stage_name" class="pill text-brand-700 bg-brand-50 dark:text-brand-300 dark:bg-brand-500/15">{{ lead.stage_name }}</span>
              </div>
              <h1 class="text-xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 break-words leading-tight">{{ lead.full_name }}</h1>
              <div class="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span v-if="lead.source_name">
                  Manba: <strong class="text-slate-700 dark:text-slate-300">{{ lead.source_name }}</strong>
                </span>
                <!-- Currently-assigned operator. Clickable on admin/sa
                     so they can jump straight to that user's profile to
                     audit workload or contact info. -->
                <span v-if="lead.assigned_to_name" class="inline-flex items-center gap-1">
                  Operator:
                  <RouterLink v-if="lead.assigned_to_id && !isOperatorPanel"
                              :to="`/admin/users/${lead.assigned_to_id}/edit`"
                              class="text-slate-700 dark:text-slate-300 font-semibold hover:text-brand-600 dark:hover:text-brand-300 hover:underline">
                    {{ lead.assigned_to_name }}
                  </RouterLink>
                  <strong v-else class="text-slate-700 dark:text-slate-300">{{ lead.assigned_to_name }}</strong>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick contact buttons -->
        <div class="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-2">
          <a :href="`tel:${lead.phone}`"
             class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-slate-800/40 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40 transition-colors group">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-emerald-500 text-white shrink-0">
              <Phone class="w-4 h-4" />
            </span>
            <div class="min-w-0">
              <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Qo'ng'iroq</div>
              <div class="font-mono text-sm text-slate-900 dark:text-slate-100 truncate">{{ formatPhone(lead.phone) }}</div>
            </div>
          </a>
          <a v-if="lead.telegram_username" :href="`https://t.me/${lead.telegram_username}`" target="_blank" rel="noopener"
             class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-slate-800/40 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40 transition-colors group">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-sky-500 text-white shrink-0">
              <Send class="w-4 h-4" />
            </span>
            <div class="min-w-0">
              <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Telegram</div>
              <div class="font-mono text-sm text-slate-900 dark:text-slate-100 truncate">@{{ lead.telegram_username }}</div>
            </div>
          </a>
          <a :href="`sms:${lead.phone}`"
             class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-slate-800/40 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40 transition-colors group">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-violet-500 text-white shrink-0">
              <MessageCircle class="w-4 h-4" />
            </span>
            <div class="min-w-0">
              <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">SMS</div>
              <div class="text-sm text-slate-900 dark:text-slate-100 truncate">Yuborish</div>
            </div>
          </a>
          <div class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 ring-1 ring-slate-200/70 dark:ring-slate-700/40">
            <span class="grid place-items-center w-9 h-9 rounded-lg bg-amber-500 text-white shrink-0">
              <Clock class="w-4 h-4" />
            </span>
            <div class="min-w-0">
              <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Yaratildi</div>
              <div class="text-sm text-slate-900 dark:text-slate-100 truncate">{{ fmtDate(lead.created_at) }}</div>
            </div>
          </div>
        </div>

        <!-- Primary action buttons (big) -->
        <div v-if="lead.status === 'open'" class="mt-5 flex flex-wrap items-center gap-2">
          <button v-if="isTerminal"
                  class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm hover:shadow transition flex-1 sm:flex-none"
                  @click="convertToApplication">
            <CheckCircle2 class="w-4 h-4" /> Arizaga o'tkazish
          </button>
          <button v-if="nextStage"
                  class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-700 text-white shadow-sm hover:shadow transition flex-1 sm:flex-none"
                  @click="moveToNext">
            <ChevronRight class="w-4 h-4" /> {{ nextStage.name }} ga o'tkazish
          </button>
          <button class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-white dark:bg-slate-800 text-rose-600 dark:text-rose-400 ring-1 ring-rose-200 dark:ring-rose-800 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition"
                  @click="showLose = true">
            <XCircle class="w-4 h-4" /> Yo'qotildi
          </button>
          <div v-if="!isOperatorPanel" class="ml-auto">
            <button v-if="!lead.application_id" class="icon-btn-danger w-10 h-10" title="O'chirish" @click="deleteLead">
              <Trash2 class="w-5 h-5" />
            </button>
          </div>
        </div>

        <div v-if="lead.status === 'lost'" class="mt-5">
          <button class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-700 text-white shadow-sm transition" @click="reopen">
            <RotateCcw class="w-4 h-4" /> Qayta ochish
          </button>
        </div>
      </div>

      <!-- Won banner -->
      <div v-if="lead.status === 'won' && lead.application_id"
           class="px-4 sm:px-6 py-3 sm:py-4 bg-emerald-50 dark:bg-emerald-900/20 border-t border-emerald-200/70 dark:border-emerald-700/30 text-sm text-emerald-800 dark:text-emerald-300 flex flex-wrap items-center justify-between gap-2 sm:gap-3">
        <span class="inline-flex items-center gap-2">
          <CheckCircle2 class="w-4 h-4 shrink-0" />
          Bu lead arizaga aylantirilgan.
          <span v-if="lead.converted_at" class="opacity-80">— {{ fmtDate(lead.converted_at) }}</span>
        </span>
        <RouterLink :to="`${panelPrefix}/applications/${lead.application_id}`" class="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-300 font-semibold hover:underline shrink-0">
          Arizaga o'tish <ArrowRight class="w-3.5 h-3.5" />
        </RouterLink>
      </div>

      <!-- Lost banner -->
      <div v-if="lead.status === 'lost'"
           class="px-4 sm:px-6 py-3 sm:py-4 bg-rose-50 dark:bg-rose-900/20 border-t border-rose-200/70 dark:border-rose-700/30 text-sm text-rose-800 dark:text-rose-300">
        <strong>Yo'qotildi.</strong> <span v-if="lead.lost_comment" class="opacity-90">Sabab: {{ lead.lost_comment }}</span>
      </div>
    </section>

    <!-- Lose modal -->
    <div v-if="showLose" class="modal-backdrop" @click.self="showLose = false">
      <div class="modal-panel max-w-md">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Lead'ni yo'qotilgan deb belgilash</h3>
        <div>
          <label class="field-label">Sabab</label>
          <SearchSelect v-model="loseForm.reason_id" :options="reasonOptions" placeholder="— tanlang —" allow-clear />
        </div>
        <div>
          <label class="field-label">Izoh (ixtiyoriy)</label>
          <textarea v-model="loseForm.comment" class="input" rows="3" placeholder="Qo'shimcha tafsilot..."></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="showLose = false">Bekor</button>
          <button class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-semibold bg-rose-600 hover:bg-rose-700 text-white" @click="loseLead">
            Yo'qotildi
          </button>
        </div>
      </div>
    </div>

    <!-- Existing applications for this phone (cross-reference card) -->
    <section v-if="relatedApps.length > 0" class="card p-4 sm:p-6 border-l-4 border-amber-400 dark:border-amber-500/70">
      <div class="flex items-start gap-3 mb-4">
        <span class="grid place-items-center w-9 h-9 rounded-lg bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300 shrink-0">
          <FileText class="w-4 h-4" />
        </span>
        <div class="flex-1 min-w-0">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">
            Bu telefon raqami bo'yicha mavjud arizalar
            <span class="text-xs font-normal text-slate-400 ml-1">({{ relatedApps.length }})</span>
          </h2>
          <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            Abituriyent allaqachon ro'yxatdan o'tgan. Tarix bilan tanishing, takroriy ariza yuborilmasligi kerak.
          </p>
        </div>
      </div>

      <ul class="space-y-2">
        <li v-for="a in relatedApps" :key="a.id">
          <RouterLink
            :to="`${panelPrefix}/applications/${a.id}`"
            class="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-500/60 hover:bg-brand-50/40 dark:hover:bg-brand-500/5 transition-colors group"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-mono text-xs font-semibold text-slate-900 dark:text-slate-100">#{{ a.application_number }}</span>
                <span v-if="a.status"
                      class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide"
                      :class="{
                        'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300': a.status === 'approved' || a.status === 'enrolled',
                        'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300': a.status === 'rejected' || a.status === 'withdrawn',
                        'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300': a.status === 'submitted' || a.status === 'under_review',
                        'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300': a.status === 'draft',
                      }">{{ a.status }}</span>
                <span v-if="a.admission_type"
                      class="text-[10px] font-medium text-slate-400 uppercase tracking-wide">{{ a.admission_type }}</span>
              </div>
              <div class="mt-0.5 text-sm text-slate-700 dark:text-slate-300 truncate">
                {{ a.program_name || '—' }}
                <span v-if="a.branch_name" class="text-slate-400 dark:text-slate-500"> · {{ a.branch_name }}</span>
              </div>
              <div v-if="a.created_at" class="mt-0.5 text-[11px] text-slate-400 dark:text-slate-500">
                Yaratilgan: {{ new Date(a.created_at).toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short', year: 'numeric' }) }}
              </div>
            </div>
            <ExternalLink class="w-4 h-4 text-slate-400 group-hover:text-brand-600 dark:group-hover:text-brand-300 shrink-0 transition-colors" />
          </RouterLink>
        </li>
      </ul>
    </section>

    <div class="grid lg:grid-cols-3 gap-4 sm:gap-5">
      <!-- LEFT: timeline + comment -->
      <div class="lg:col-span-2 space-y-4 sm:space-y-5">
        <section class="card p-4 sm:p-6">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-4 inline-flex items-center gap-2">
            <span class="grid place-items-center w-7 h-7 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
              <Activity class="w-3.5 h-3.5" />
            </span>
            Faoliyat tarixi
            <span class="text-xs font-normal text-slate-400">({{ activities.length }})</span>
          </h2>

          <!-- Add comment / log call -->
          <div v-if="lead.status === 'open'" class="mb-5">
            <textarea v-model="newComment" rows="2" class="input w-full resize-none" placeholder="Izoh qoldiring — suhbat tafsilotlari, kelishuvlar..."></textarea>
            <div class="mt-2 flex flex-wrap gap-2">
              <button class="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:hover:bg-emerald-600 text-white shadow-sm transition-colors"
                      :disabled="loggingCall" @click="logCall" title="Qo'ng'iroq qilganligingizni qayd etish">
                <Phone class="w-4 h-4" />
                {{ loggingCall ? 'Qayd etilmoqda...' : "Qo'ng'iroq qildim" }}
              </button>
              <button class="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:hover:bg-brand-600 text-white shadow-sm transition-colors"
                      :disabled="sending || !newComment.trim()" @click="addComment">
                <Send class="w-4 h-4" />
                {{ sending ? 'Yuborilmoqda...' : 'Izoh saqlash' }}
              </button>
              <span class="ml-auto self-center text-[11px] text-slate-400 dark:text-slate-500">
                Izoh ixtiyoriy — bo'sh qoldirilsa ham qo'ng'iroq qayd etiladi
              </span>
            </div>
          </div>

          <!-- Timeline -->
          <ol v-if="activities.length" class="relative pl-7 space-y-5 border-l-2 border-slate-200 dark:border-slate-800">
            <li v-for="a in activities.slice().reverse()" :key="a.id" class="relative">
              <span class="absolute -left-[33px] top-0.5 grid place-items-center w-6 h-6 rounded-full bg-white dark:bg-slate-900 ring-2"
                    :class="a.action === 'convert' ? 'ring-emerald-500'
                          : a.action === 'lose' ? 'ring-rose-500'
                          : a.action === 'sla_alert' ? 'ring-amber-500'
                          : a.action === 'stage_move' ? 'ring-brand-500'
                          : a.action === 'call' ? 'ring-emerald-500'
                          : 'ring-slate-300 dark:ring-slate-700'">
                <component :is="a.action === 'convert' ? CheckCircle2
                              : a.action === 'lose' ? XCircle
                              : a.action === 'sla_alert' ? Clock
                              : a.action === 'comment' ? MessageCircle
                              : a.action === 'call' ? Phone
                              : a.action === 'stage_move' ? ArrowRight
                              : a.action === 'assign' ? UserIcon
                              : Activity"
                           class="w-3 h-3"
                           :class="a.action === 'convert' ? 'text-emerald-600'
                                 : a.action === 'lose' ? 'text-rose-600'
                                 : a.action === 'sla_alert' ? 'text-amber-600'
                                 : a.action === 'stage_move' ? 'text-brand-600'
                                 : a.action === 'call' ? 'text-emerald-600'
                                 : 'text-slate-500'" />
              </span>
              <div class="text-xs text-slate-500 dark:text-slate-400 inline-flex items-center gap-1.5 flex-wrap">
                <Clock class="w-3 h-3" /> {{ fmtDate(a.created_at) }}
                <span v-if="a.user_full_name || a.user_phone" class="text-slate-400">·</span>
                <RouterLink v-if="(a.user_full_name || a.user_phone) && a.user_id && !isOperatorPanel"
                            :to="`/admin/users/${a.user_id}/edit`"
                            class="text-slate-700 dark:text-slate-300 font-medium hover:text-brand-600 dark:hover:text-brand-300 hover:underline">
                  {{ a.user_full_name || a.user_phone }}
                </RouterLink>
                <span v-else-if="a.user_full_name || a.user_phone" class="text-slate-700 dark:text-slate-300 font-medium">{{ a.user_full_name || a.user_phone }}</span>
              </div>
              <div class="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">
                {{ ACTION_LABELS[a.action] || a.action }}
                <template v-if="a.action === 'stage_move' && a.from_stage_name && a.to_stage_name">
                  <span class="text-slate-500 font-normal">: {{ a.from_stage_name }}</span>
                  <ArrowRight class="inline w-3 h-3 mx-1 text-slate-400" />
                  <span class="text-brand-600 dark:text-brand-300">{{ a.to_stage_name }}</span>
                </template>
              </div>
              <p v-if="a.comment" class="mt-1.5 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{{ a.comment }}</p>
            </li>
          </ol>
          <div v-else class="text-sm text-slate-400 text-center py-8 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
            <Activity class="w-6 h-6 mx-auto mb-2 text-slate-300 dark:text-slate-700" />
            Hali faoliyat yo'q
          </div>
        </section>
      </div>

      <!-- RIGHT: actions + meta -->
      <div class="space-y-4 sm:space-y-5">
        <section v-if="lead.status === 'open'" class="card p-4 sm:p-5">
          <div class="space-y-4">
            <div>
              <label class="field-label inline-flex items-center gap-1.5">
                <ChevronRight class="w-3 h-3" /> Bosqich
              </label>
              <SearchSelect :model-value="lead.stage_id"
                            :options="stageOptions" placeholder="— tanlang —"
                            @update:model-value="(v) => v && moveTo(v)" />
            </div>

            <div v-if="!isOperatorPanel" class="pt-3 border-t border-slate-100 dark:border-slate-800">
              <label class="field-label inline-flex items-center gap-1.5">
                <UserIcon class="w-3 h-3" /> Operator
              </label>
              <SearchSelect :model-value="lead.assigned_to_id || ''"
                            :options="operatorOptions" placeholder="— biriktirilmagan —" allow-clear
                            @update:model-value="(v) => changeAssignee(v || null)" />
              <button class="mt-2 inline-flex items-center justify-center gap-1.5 w-full px-3 py-2 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40 transition-colors"
                      @click="autoAssign">
                <RotateCcw class="w-3 h-3" /> Avto-biriktirish (kam yuklamaliga)
              </button>
            </div>
          </div>
        </section>

        <!-- Schedule next callback (operator + admin) -->
        <section v-if="lead.status === 'open'" class="card p-4 sm:p-5">
          <div class="flex items-center justify-between mb-3">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <span class="grid place-items-center w-7 h-7 rounded-lg"
                    :class="scheduleStatus === 'overdue'
                      ? 'bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-300'
                      : scheduleStatus === 'today'
                        ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300'
                        : 'bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-300'">
                <Clock class="w-3.5 h-3.5" />
              </span>
              Keyingi aloqa
            </h2>
            <button v-if="!showSchedule"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40 transition-colors"
                    @click="openScheduleForm">
              <Pencil class="w-3 h-3" /> {{ lead.next_contact_at ? 'Tahrirlash' : "O'rnatish" }}
            </button>
          </div>

          <!-- Schedule form -->
          <div v-if="showSchedule" class="space-y-3">
            <div>
              <label class="field-label">Sana va vaqt</label>
              <input v-model="scheduleForm.next_contact_at" type="datetime-local"
                     class="input" :min="toLocalInput(new Date())" />
            </div>
            <div>
              <label class="field-label">Eslatma (ixtiyoriy)</label>
              <textarea v-model="scheduleForm.note" rows="2" class="input"
                        placeholder="Masalan: ariza haqida qaytadan tushuntirish..."></textarea>
            </div>
            <div class="flex gap-2 pt-2">
              <button class="btn-primary btn-sm flex-1" @click="saveSchedule">
                <CheckCircle2 class="w-3.5 h-3.5" /> Saqlash
              </button>
              <button class="btn-ghost btn-sm" @click="showSchedule = false">Bekor</button>
            </div>
          </div>

          <!-- Read-only display -->
          <div v-else-if="lead.next_contact_at" class="space-y-2">
            <div class="rounded-lg p-3 ring-1"
                 :class="scheduleStatus === 'overdue'
                   ? 'bg-rose-50 ring-rose-200 dark:bg-rose-500/10 dark:ring-rose-700/40'
                   : scheduleStatus === 'today'
                     ? 'bg-amber-50 ring-amber-200 dark:bg-amber-500/10 dark:ring-amber-700/40'
                     : 'bg-violet-50 ring-violet-200 dark:bg-violet-500/10 dark:ring-violet-700/40'">
              <div class="flex items-center gap-2 text-sm font-bold"
                   :class="scheduleStatus === 'overdue'
                     ? 'text-rose-700 dark:text-rose-300'
                     : scheduleStatus === 'today'
                       ? 'text-amber-700 dark:text-amber-300'
                       : 'text-violet-700 dark:text-violet-300'">
                <Clock class="w-4 h-4 shrink-0" />
                {{ fmtSchedule(lead.next_contact_at) }}
                <span v-if="scheduleStatus === 'overdue'" class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-500/20 ml-auto">muddati o'tdi</span>
                <span v-else-if="scheduleStatus === 'today'" class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-500/20 ml-auto">bugun</span>
              </div>
              <p v-if="lead.next_contact_note" class="mt-1.5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed whitespace-pre-wrap">{{ lead.next_contact_note }}</p>
            </div>
            <button class="w-full text-[11px] text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
                    @click="clearSchedule">
              Eslatmani o'chirish
            </button>
          </div>

          <div v-else class="text-center py-3 text-xs text-slate-400">
            Eslatma o'rnatilmagan
          </div>
        </section>

        <section class="card p-4 sm:p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <span class="grid place-items-center w-7 h-7 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
                <UserIcon class="w-3.5 h-3.5" />
              </span>
              Lead ma'lumotlari
            </h2>
            <button v-if="!editMode && lead.status !== 'lost'"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/70 dark:ring-slate-700/40 transition-colors"
                    @click="enterEditMode">
              <Pencil class="w-3 h-3" /> Tahrirlash
            </button>
          </div>

          <!-- Read-only — icon + label + value -->
          <template v-if="!editMode">
            <ul class="space-y-2.5">
              <li class="flex items-start gap-3">
                <UserIcon class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">F.I.Sh.</div>
                  <div class="text-sm text-slate-900 dark:text-slate-100">{{ lead.full_name }}</div>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <Phone class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Telefon</div>
                  <div class="text-sm font-mono text-slate-900 dark:text-slate-100">{{ formatPhone(lead.phone) }}</div>
                </div>
              </li>
              <li v-if="lead.telegram_username" class="flex items-start gap-3">
                <Send class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Telegram</div>
                  <div class="text-sm font-mono text-slate-900 dark:text-slate-100">@{{ lead.telegram_username }}</div>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <ChevronRight class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Yo'nalish</div>
                  <div class="text-sm text-slate-900 dark:text-slate-100">{{ lead.program_name || '—' }}</div>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <ChevronRight class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Filial</div>
                  <div class="text-sm text-slate-900 dark:text-slate-100">{{ lead.branch_name || '—' }}</div>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <ChevronRight class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Manba</div>
                  <div class="text-sm text-slate-900 dark:text-slate-100">{{ lead.source_name || '—' }}</div>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <Clock class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Yaratildi</div>
                  <div class="text-sm text-slate-900 dark:text-slate-100">{{ fmtDate(lead.created_at) }}</div>
                </div>
              </li>
            </ul>
            <div v-if="lead.notes" class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
              <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Eslatma</div>
              <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{{ lead.notes }}</p>
            </div>
          </template>

          <!-- Edit form -->
          <div v-else class="space-y-3.5">
            <div>
              <label class="field-label">F.I.Sh.</label>
              <input v-model="editForm.full_name" class="input" />
            </div>
            <div>
              <label class="field-label">Telefon</label>
              <input :value="editForm.phone" class="input font-mono" inputmode="tel"
                     :placeholder="PLACEHOLDERS.phoneUz"
                     @input="(e) => editForm.phone = formatPhone((e.target as HTMLInputElement).value)" />
            </div>
            <div>
              <label class="field-label">Telegram</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-mono pointer-events-none">@</span>
                <input v-model="editForm.telegram_username" class="input pl-7 font-mono" placeholder="username" />
              </div>
            </div>
            <div>
              <label class="field-label">Manba</label>
              <SearchSelect v-model="editForm.source_id" :options="sourceOptions" placeholder="— tanlang —" allow-clear />
            </div>
            <div>
              <label class="field-label">Filial</label>
              <SearchSelect v-model="editForm.branch_id" :options="branchOptions" placeholder="— tanlang —" allow-clear />
            </div>
            <div>
              <label class="field-label">Yo'nalish</label>
              <SearchSelect v-model="editForm.program_id" :options="programOptions" placeholder="— tanlang —" allow-clear :disabled="!editForm.branch_id" />
            </div>
            <div>
              <label class="field-label">Eslatma</label>
              <textarea v-model="editForm.notes" class="input" rows="3"></textarea>
            </div>
            <div class="flex gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
              <button class="btn-primary flex-1 justify-center" :disabled="saving" @click="saveEdit">
                <CheckCircle2 class="w-4 h-4" />
                {{ saving ? 'Saqlanmoqda...' : 'Saqlash' }}
              </button>
              <button class="btn-outline" @click="cancelEdit">Bekor</button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
