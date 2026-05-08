<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Plus, List as ListIcon, CheckCircle2, Phone, GripVertical, Send,
  ArrowRight, MoreVertical, Clock,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { leadsApi, type Lead, type LeadBoardResponse, type LeadPipeline } from '@/api/leads.api'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import { useToast } from '@/composables/useToast'
import { formatPhone } from '@/utils/validators'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const toast = useToast()

const myOnly = computed(() => !!route.meta?.myOnly)
const panelPrefix = computed(() => route.path.startsWith('/operator/') ? '/operator' : '/admin')

const pipelines = ref<LeadPipeline[]>([])
const pipelineId = ref('')
const board = ref<LeadBoardResponse | null>(null)
const loading = ref(false)

const pipelineOptions = computed(() => pipelines.value.map(p => ({ id: p.id, label: p.name })))

const totalLeads = computed(() => board.value?.stages.reduce((s, st) => s + st.leads.length, 0) ?? 0)

async function load() {
  if (!pipelineId.value) return
  loading.value = true
  try {
    const res = await leadsApi.board(pipelineId.value)
    if (myOnly.value && auth.user?.id) {
      // Filter to only leads assigned to current operator
      const me = auth.user.id
      res.stages = res.stages.map(s => ({
        ...s,
        leads: s.leads.filter(l => l.assigned_to_id === me),
      }))
    }
    board.value = res
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  pipelines.value = await leadsApi.pipelines.list().catch(() => [])
  const def = pipelines.value.find(p => p.is_default) || pipelines.value[0]
  if (def) pipelineId.value = def.id
  await load()
})

watch(pipelineId, load)

// === Drag & drop ===
const draggingId = ref<string | null>(null)
const dragOverStage = ref<string | null>(null)

function onDragStart(e: DragEvent, lead: Lead) {
  draggingId.value = lead.id
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/lead-id', lead.id)
  }
}
function onDragEnd() {
  draggingId.value = null
  dragOverStage.value = null
}
function onDragOver(e: DragEvent, stageId: string) {
  e.preventDefault()
  dragOverStage.value = stageId
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}
function onDragLeave(stageId: string) {
  if (dragOverStage.value === stageId) dragOverStage.value = null
}
async function onDrop(e: DragEvent, toStageId: string) {
  e.preventDefault()
  dragOverStage.value = null
  const leadId = e.dataTransfer?.getData('text/lead-id') || draggingId.value
  if (!leadId || !board.value) return
  const lead = findLead(leadId)
  if (!lead || lead.stage_id === toStageId) return

  // Optimistic UI: move card immediately
  const fromStage = board.value.stages.find(s => s.id === lead.stage_id)
  const toStage = board.value.stages.find(s => s.id === toStageId)
  if (!fromStage || !toStage) return
  fromStage.leads = fromStage.leads.filter(l => l.id !== leadId)
  toStage.leads.unshift({ ...lead, stage_id: toStageId, stage_name: toStage.name })

  try {
    await leadsApi.move(leadId, toStageId)
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
    await load()
  }
}

function findLead(id: string): Lead | null {
  if (!board.value) return null
  for (const s of board.value.stages) {
    const l = s.leads.find(x => x.id === id)
    if (l) return l
  }
  return null
}

function avatarInitials(s: string): string {
  const parts = (s || '').split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '—'
}
function relTime(iso: string): string {
  const d = new Date(iso); const diff = Date.now() - d.getTime()
  if (diff < 3600_000) return `${Math.max(Math.floor(diff / 60_000), 1)} daq`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat`
  return `${Math.floor(diff / 86_400_000)} kun`
}

async function convertLead(lead: Lead) {
  router.push({ path: `${panelPrefix.value}/applications/new`, query: { lead_id: lead.id } })
}
</script>

<template>
  <div>
    <PageHeader
      :title="myOnly ? `Mening kanban` : 'Kanban (varonka)'"
      :subtitle="`Bosqichma-bosqich varonka. Lead'larni sudrab keyingi bosqichga o'tkazing${board ? ' · Jami ' + totalLeads + ' ta' : ''}`"
      :crumbs="[{ label: 'Bosh sahifa', to: panelPrefix }, { label: 'CRM', to: `${panelPrefix}/leads` }]"
    >
      <div class="min-w-[240px]">
        <SearchSelect v-model="pipelineId" :options="pipelineOptions" placeholder="Varonkani tanlang" />
      </div>
      <RouterLink :to="`${panelPrefix}/leads`" class="btn-outline">
        <ListIcon class="w-4 h-4" /> Ro'yxat
      </RouterLink>
      <RouterLink :to="`${panelPrefix}/leads/new`" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi
      </RouterLink>
    </PageHeader>

    <Skeleton v-if="loading" type="kanban" />
    <div v-else-if="!board" class="card p-12 text-center text-slate-500">Varonka tanlang</div>

    <!-- Kanban -->
    <div v-else class="overflow-x-auto pb-4 -mx-4 px-4">
      <div class="flex items-stretch gap-4 min-w-max">
        <section
          v-for="stage in board.stages"
          :key="stage.id"
          class="w-[320px] shrink-0 rounded-2xl bg-slate-100/80 dark:bg-slate-900/60 border-2 transition-colors flex flex-col max-h-[calc(100vh-220px)]"
          :class="dragOverStage === stage.id
            ? 'border-brand-400 bg-brand-50/50 dark:bg-brand-500/10'
            : stage.is_terminal
              ? 'border-emerald-200/60 dark:border-emerald-800/40'
              : 'border-transparent'"
          @dragover="onDragOver($event, stage.id)"
          @dragleave="onDragLeave(stage.id)"
          @drop="onDrop($event, stage.id)">

          <!-- Column header -->
          <header class="px-4 py-3 sticky top-0 bg-slate-100/80 dark:bg-slate-900/60 backdrop-blur rounded-t-2xl">
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <span class="w-2.5 h-2.5 rounded-full ring-2 ring-white dark:ring-slate-900 shrink-0"
                      :style="{ backgroundColor: stage.color || '#94a3b8' }"></span>
                <h2 class="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">{{ stage.name }}</h2>
                <CheckCircle2 v-if="stage.is_terminal" class="w-4 h-4 text-emerald-500 shrink-0" />
              </div>
              <span class="inline-flex items-center justify-center min-w-[26px] h-6 px-1.5 rounded-full text-[11px] font-bold tabular-nums"
                    :class="stage.leads.length === 0
                      ? 'bg-slate-200 dark:bg-slate-800 text-slate-500'
                      : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 ring-1 ring-slate-200 dark:ring-slate-700'">
                {{ stage.leads.length }}
              </span>
            </div>
            <!-- Stage colored progress strip -->
            <div class="mt-2 h-1 rounded-full bg-slate-200/60 dark:bg-slate-800/60 overflow-hidden">
              <div class="h-full rounded-full" :style="{ width: '100%', backgroundColor: stage.color || '#94a3b8' }"></div>
            </div>
          </header>

          <!-- Cards -->
          <div class="p-3 space-y-2.5 overflow-y-auto flex-1">
            <article
              v-for="lead in stage.leads"
              :key="lead.id"
              draggable="true"
              :class="draggingId === lead.id ? 'opacity-40 scale-95' : ''"
              class="group bg-white dark:bg-slate-900 rounded-xl border border-slate-200/70 dark:border-slate-800 p-3.5 shadow-sm hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all cursor-grab active:cursor-grabbing"
              @dragstart="onDragStart($event, lead)"
              @dragend="onDragEnd"
              @click="router.push(`${panelPrefix}/leads/${lead.id}`)">

              <div class="flex items-start gap-3 mb-2">
                <div class="grid place-items-center w-10 h-10 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300 text-xs font-bold shrink-0">
                  {{ avatarInitials(lead.full_name) }}
                </div>
                <div class="min-w-0 flex-1">
                  <div class="text-sm font-bold text-slate-900 dark:text-slate-100 truncate group-hover:text-brand-700 dark:group-hover:text-brand-300 transition-colors">{{ lead.full_name }}</div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 inline-flex items-center gap-1 font-mono mt-0.5">
                    <Phone class="w-3 h-3" /> {{ formatPhone(lead.phone) }}
                  </div>
                </div>
                <GripVertical class="w-4 h-4 text-slate-300 dark:text-slate-700 group-hover:text-slate-500 transition-colors shrink-0" />
              </div>

              <div v-if="lead.program_name || lead.branch_name" class="space-y-0.5 pt-2 border-t border-slate-100 dark:border-slate-800/60">
                <div v-if="lead.program_name" class="text-xs text-slate-700 dark:text-slate-300 truncate">{{ lead.program_name }}</div>
                <div v-if="lead.branch_name" class="text-[11px] text-slate-500 dark:text-slate-400 truncate">{{ lead.branch_name }}</div>
              </div>

              <div class="mt-2.5 flex items-center justify-between gap-2 text-[11px]">
                <span v-if="lead.source_name" class="inline-flex items-center px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-medium">
                  {{ lead.source_name }}
                </span>
                <span v-else class="text-slate-300">—</span>
                <span class="text-slate-500 dark:text-slate-400 inline-flex items-center gap-1">
                  <Clock class="w-3 h-3" /> {{ relTime(lead.created_at) }}
                </span>
              </div>

              <div v-if="lead.assigned_to_name && !myOnly" class="mt-2 text-[11px] text-slate-500 dark:text-slate-400 truncate">
                Operator: <span class="text-slate-700 dark:text-slate-300 font-medium">{{ lead.assigned_to_name }}</span>
              </div>

              <!-- Quick action buttons (tel + telegram) -->
              <div class="mt-3 flex items-center gap-1.5">
                <a :href="`tel:${lead.phone}`" @click.stop
                   class="flex-1 inline-flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-[11px] font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300 dark:hover:bg-emerald-500/25 transition-colors"
                   title="Qo'ng'iroq qilish">
                  <Phone class="w-3 h-3" /> Qo'ng'iroq
                </a>
                <a v-if="lead.telegram_username"
                   :href="`https://t.me/${lead.telegram_username}`" target="_blank" rel="noopener" @click.stop
                   class="flex-1 inline-flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-[11px] font-semibold bg-sky-50 hover:bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300 dark:hover:bg-sky-500/25 transition-colors"
                   title="Telegram">
                  <Send class="w-3 h-3" /> Telegram
                </a>
              </div>

              <!-- Convert button on terminal stage -->
              <button v-if="stage.is_terminal" type="button"
                      class="mt-2 w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm hover:shadow transition"
                      @click.stop="convertLead(lead)">
                <CheckCircle2 class="w-3.5 h-3.5" /> Arizaga o'tkazish
                <ArrowRight class="w-3 h-3 ml-auto" />
              </button>
            </article>

            <div v-if="!stage.leads.length"
                 class="text-center py-8 px-3 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              <div class="text-xs text-slate-400">Bo'sh</div>
              <div class="text-[10px] text-slate-400 mt-0.5">Lead'ni shu yerga sudrang</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
