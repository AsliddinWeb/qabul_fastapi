<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Plus, Pencil, Trash2, Save, X as XIcon, Star, GitMerge, Tag, MinusCircle,
  ArrowUp, ArrowDown, CheckCircle2,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import {
  leadsApi,
  type LeadPipeline, type LeadStage, type LeadSource, type LeadLostReason,
} from '@/api/leads.api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import SearchSelect from '@/components/ui/SearchSelect.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const toast = useToast()
const { ask } = useConfirm()

const tab = ref<'pipelines' | 'stages' | 'sources' | 'reasons'>('pipelines')
const loading = ref(true)

// === Pipelines ===
const pipelines = ref<LeadPipeline[]>([])
const editingPipeline = ref<Partial<LeadPipeline> | null>(null)

async function loadPipelines() { pipelines.value = await leadsApi.pipelines.list() }

function openPipeline(p?: LeadPipeline) {
  editingPipeline.value = p
    ? { ...p }
    : { name: '', description: '', is_default: false, is_active: true, order_index: pipelines.value.length }
}
async function savePipeline() {
  const p = editingPipeline.value!
  if (!p.name?.trim()) return toast.error("Nomi shart")
  try {
    if (p.id) await leadsApi.pipelines.update(p.id, p as any)
    else      await leadsApi.pipelines.create(p as any)
    toast.success("Saqlandi")
    editingPipeline.value = null
    await loadPipelines()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}
async function deletePipeline(p: LeadPipeline) {
  const ok = await ask({ title: "Varonkani o'chirish", message: `${p.name} o'chirilsinmi?`, tone: 'danger', confirmLabel: "O'chirish" })
  if (!ok) return
  try {
    await leadsApi.pipelines.delete(p.id)
    toast.success("O'chirildi")
    await loadPipelines()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "O'chirib bo'lmadi")
  }
}

// === Stages ===
const stagePipeline = ref('')
const stages = ref<LeadStage[]>([])
const editingStage = ref<Partial<LeadStage> | null>(null)

const pipelineOptions = computed(() => pipelines.value.map(p => ({ id: p.id, label: p.name })))

async function loadStages() {
  if (!stagePipeline.value) { stages.value = []; return }
  stages.value = await leadsApi.stages.list(stagePipeline.value)
}
watch(stagePipeline, loadStages)

function openStage(s?: LeadStage) {
  editingStage.value = s
    ? { ...s }
    : {
        pipeline_id: stagePipeline.value, name: '',
        order_index: stages.value.length, color: '#94a3b8',
        is_terminal: false, is_active: true,
      }
}
async function saveStage() {
  const s = editingStage.value!
  if (!s.name?.trim()) return toast.error("Nomi shart")
  if (!s.pipeline_id) return toast.error("Varonka shart")
  try {
    if (s.id) await leadsApi.stages.update(s.id, s as any)
    else      await leadsApi.stages.create(s as any)
    toast.success("Saqlandi")
    editingStage.value = null
    await loadStages()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}
async function deleteStage(s: LeadStage) {
  const ok = await ask({ title: "Bosqichni o'chirish", message: `${s.name} o'chirilsinmi?`, tone: 'danger', confirmLabel: "O'chirish" })
  if (!ok) return
  try {
    await leadsApi.stages.delete(s.id)
    toast.success("O'chirildi")
    await loadStages()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "O'chirib bo'lmadi")
  }
}
async function moveStage(s: LeadStage, dir: -1 | 1) {
  const sorted = [...stages.value].sort((a, b) => a.order_index - b.order_index)
  const idx = sorted.findIndex(x => x.id === s.id)
  const swap = sorted[idx + dir]
  if (!swap) return
  try {
    await Promise.all([
      leadsApi.stages.update(s.id, { order_index: swap.order_index }),
      leadsApi.stages.update(swap.id, { order_index: s.order_index }),
    ])
    await loadStages()
  } catch { toast.error("Tartib o'zgartirib bo'lmadi") }
}

// === Sources ===
const sources = ref<LeadSource[]>([])
const editingSource = ref<Partial<LeadSource> | null>(null)

async function loadSources() { sources.value = await leadsApi.sources.list() }

function openSource(s?: LeadSource) {
  editingSource.value = s ? { ...s } : { code: '', name: '', is_active: true, order_index: sources.value.length }
}
async function saveSource() {
  const s = editingSource.value!
  if (!s.code?.trim() || !s.name?.trim()) return toast.error("Kod va nomi shart")
  try {
    if (s.id) await leadsApi.sources.update(s.id, s as any)
    else      await leadsApi.sources.create(s as any)
    toast.success("Saqlandi")
    editingSource.value = null
    await loadSources()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}
async function deleteSource(s: LeadSource) {
  const ok = await ask({ title: "Manbani o'chirish", message: `${s.name} o'chirilsinmi?`, tone: 'danger', confirmLabel: "O'chirish" })
  if (!ok) return
  try { await leadsApi.sources.delete(s.id); toast.success("O'chirildi"); await loadSources() }
  catch { toast.error("O'chirib bo'lmadi") }
}

// === Lost reasons ===
const reasons = ref<LeadLostReason[]>([])
const editingReason = ref<Partial<LeadLostReason> | null>(null)

async function loadReasons() { reasons.value = await leadsApi.lostReasons.list() }
function openReason(r?: LeadLostReason) {
  editingReason.value = r ? { ...r } : { name: '', is_active: true, order_index: reasons.value.length }
}
async function saveReason() {
  const r = editingReason.value!
  if (!r.name?.trim()) return toast.error("Nomi shart")
  try {
    if (r.id) await leadsApi.lostReasons.update(r.id, r as any)
    else      await leadsApi.lostReasons.create(r as any)
    toast.success("Saqlandi")
    editingReason.value = null
    await loadReasons()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xatolik")
  }
}
async function deleteReason(r: LeadLostReason) {
  const ok = await ask({ title: "Sababni o'chirish", message: `${r.name} o'chirilsinmi?`, tone: 'danger', confirmLabel: "O'chirish" })
  if (!ok) return
  try { await leadsApi.lostReasons.delete(r.id); toast.success("O'chirildi"); await loadReasons() }
  catch { toast.error("O'chirib bo'lmadi") }
}

onMounted(async () => {
  try {
    await loadPipelines()
    if (pipelines.value.length) stagePipeline.value = pipelines.value.find(p => p.is_default)?.id || pipelines.value[0].id
    await Promise.all([loadStages(), loadSources(), loadReasons()])
  } finally {
    loading.value = false
  }
})

const tabs = [
  { id: 'pipelines', label: 'Varonkalar',     icon: GitMerge },
  { id: 'stages',    label: 'Bosqichlar',     icon: MinusCircle },
  { id: 'sources',   label: 'Manbalar',       icon: Tag },
  { id: 'reasons',   label: "Yo'qotish sabablari", icon: XIcon },
]

// Per-source colored chip palette (matches list page)
const SOURCE_TONE: Record<string, string> = {
  web_form:  'bg-sky-100 text-sky-600 dark:bg-sky-500/15 dark:text-sky-300',
  telegram:  'bg-cyan-100 text-cyan-600 dark:bg-cyan-500/15 dark:text-cyan-300',
  instagram: 'bg-pink-100 text-pink-600 dark:bg-pink-500/15 dark:text-pink-300',
  call:      'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300',
  walk_in:   'bg-amber-100 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300',
  referral:  'bg-violet-100 text-violet-600 dark:bg-violet-500/15 dark:text-violet-300',
  agent:     'bg-indigo-100 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300',
}
</script>

<template>
  <div class="space-y-5">
    <PageHeader
      title="Lead sozlamalari"
      subtitle="Varonkalar, bosqichlar, manbalar va yo'qotish sabablarini boshqaring"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'CRM', to: '/admin/leads' }]"
    />

    <!-- Tabs (pill style) -->
    <div class="card p-1 inline-flex items-center gap-1 overflow-x-auto">
      <button v-for="t in tabs" :key="t.id"
              class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
              :class="tab === t.id
                ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
                : 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800/60'"
              @click="tab = t.id as any">
        <component :is="t.icon" class="w-4 h-4" /> {{ t.label }}
      </button>
    </div>

    <Skeleton v-if="loading" type="list" />

    <template v-else>
    <!-- ===== Pipelines ===== -->
    <div v-if="tab === 'pipelines'" class="card">
      <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h2 class="text-base font-semibold text-slate-900 dark:text-slate-100">Varonkalar</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Lead qabul jarayoni uchun pipeline'lar — masalan "Yangi qabul", "Perevod"</p>
        </div>
        <button class="btn-primary" @click="openPipeline()">
          <Plus class="w-4 h-4" /> Yangi varonka
        </button>
      </div>
      <ul class="divide-y divide-slate-100 dark:divide-slate-800">
        <li v-for="p in pipelines" :key="p.id"
            class="p-5 flex items-center justify-between gap-4 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 shrink-0">
              <GitMerge class="w-5 h-5" />
            </span>
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">{{ p.name }}</span>
                <span v-if="p.is_default" class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300 ring-1 ring-brand-200 dark:ring-brand-700/40 font-medium">
                  <Star class="w-2.5 h-2.5 fill-current" /> Default
                </span>
                <span v-if="!p.is_active" class="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 ring-1 ring-slate-200">Faol emas</span>
              </div>
              <div v-if="p.description" class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{{ p.description }}</div>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button class="btn-outline btn-sm" @click="openPipeline(p)"><Pencil class="w-3.5 h-3.5" /> Tahrirlash</button>
            <button class="icon-btn-danger" :title="'O\'chirish'" @click="deletePipeline(p)"><Trash2 class="w-4 h-4" /></button>
          </div>
        </li>
        <li v-if="!pipelines.length" class="p-12 text-center">
          <GitMerge class="w-8 h-8 text-slate-300 dark:text-slate-700 mx-auto mb-3" />
          <div class="text-sm text-slate-500 dark:text-slate-400">Hali varonka yo'q</div>
          <button class="btn-primary mt-4" @click="openPipeline()">
            <Plus class="w-4 h-4" /> Birinchi varonkani yaratish
          </button>
        </li>
      </ul>
    </div>

    <!-- ===== Stages ===== -->
    <div v-if="tab === 'stages'" class="space-y-4">
      <div class="card p-5 flex flex-wrap items-end justify-between gap-4">
        <div class="min-w-[300px] flex-1">
          <label class="field-label">Varonka</label>
          <SearchSelect v-model="stagePipeline" :options="pipelineOptions" placeholder="— tanlang —" />
        </div>
        <button class="btn-primary" :disabled="!stagePipeline" @click="openStage()">
          <Plus class="w-4 h-4" /> Yangi bosqich
        </button>
      </div>
      <div class="card">
        <ul class="divide-y divide-slate-100 dark:divide-slate-800">
          <li v-for="(s, idx) in stages" :key="s.id"
              class="p-4 flex items-center gap-4 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
            <!-- Position number -->
            <span class="grid place-items-center w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs font-bold shrink-0">{{ idx + 1 }}</span>
            <!-- Color swatch -->
            <span class="w-6 h-6 rounded-lg shrink-0 ring-2 ring-white dark:ring-slate-900 shadow-sm"
                  :style="{ backgroundColor: s.color || '#94a3b8' }"></span>
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">{{ s.name }}</span>
                <span v-if="s.is_terminal" class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 ring-1 ring-emerald-200 dark:ring-emerald-700/40 font-medium">
                  <CheckCircle2 class="w-3 h-3" /> Yakuniy (konversiya)
                </span>
                <span v-if="!s.is_active" class="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 ring-1 ring-slate-200">Faol emas</span>
              </div>
              <div class="text-[11px] text-slate-400 mt-0.5 inline-flex items-center gap-1.5">
                <span class="font-mono">{{ s.color || '—' }}</span>
                <span class="text-slate-300">·</span>
                <span>tartib: {{ s.order_index }}</span>
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <div class="inline-flex items-center rounded-lg ring-1 ring-slate-200 dark:ring-slate-700 overflow-hidden">
                <button class="grid place-items-center w-8 h-8 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent transition" :disabled="idx === 0" @click="moveStage(s, -1)"><ArrowUp class="w-4 h-4" /></button>
                <span class="w-px h-5 bg-slate-200 dark:bg-slate-700"></span>
                <button class="grid place-items-center w-8 h-8 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent transition" :disabled="idx === stages.length - 1" @click="moveStage(s, 1)"><ArrowDown class="w-4 h-4" /></button>
              </div>
              <button class="btn-outline btn-sm" @click="openStage(s)"><Pencil class="w-3.5 h-3.5" /></button>
              <button class="icon-btn-danger" @click="deleteStage(s)"><Trash2 class="w-4 h-4" /></button>
            </div>
          </li>
          <li v-if="stagePipeline && !stages.length" class="p-12 text-center">
            <MinusCircle class="w-8 h-8 text-slate-300 dark:text-slate-700 mx-auto mb-3" />
            <div class="text-sm text-slate-500 dark:text-slate-400">Bosqich qo'shilmagan</div>
            <button class="btn-primary mt-4" @click="openStage()">
              <Plus class="w-4 h-4" /> Birinchi bosqich
            </button>
          </li>
          <li v-if="!stagePipeline" class="p-10 text-center text-sm text-slate-400">← Avval varonkani tanlang</li>
        </ul>
      </div>
    </div>

    <!-- ===== Sources ===== -->
    <div v-if="tab === 'sources'" class="card">
      <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h2 class="text-base font-semibold text-slate-900 dark:text-slate-100">Manbalar</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Lead qaerdan kelgan — telegram, instagram, sayt va h.k.</p>
        </div>
        <button class="btn-primary" @click="openSource()">
          <Plus class="w-4 h-4" /> Yangi manba
        </button>
      </div>
      <ul class="divide-y divide-slate-100 dark:divide-slate-800">
        <li v-for="s in sources" :key="s.id"
            class="p-5 flex items-center justify-between gap-4 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <span class="grid place-items-center w-10 h-10 rounded-xl shrink-0"
                  :class="SOURCE_TONE[s.code] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'">
              <Tag class="w-5 h-5" />
            </span>
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">{{ s.name }}</span>
                <code class="text-[11px] font-mono text-slate-500 px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded">{{ s.code }}</code>
                <span v-if="!s.is_active" class="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 ring-1 ring-slate-200">Faol emas</span>
              </div>
              <div class="text-[11px] text-slate-400 mt-0.5">tartib: {{ s.order_index }}</div>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button class="btn-outline btn-sm" @click="openSource(s)"><Pencil class="w-3.5 h-3.5" /> Tahrirlash</button>
            <button class="icon-btn-danger" @click="deleteSource(s)"><Trash2 class="w-4 h-4" /></button>
          </div>
        </li>
        <li v-if="!sources.length" class="p-12 text-center">
          <Tag class="w-8 h-8 text-slate-300 dark:text-slate-700 mx-auto mb-3" />
          <div class="text-sm text-slate-500 dark:text-slate-400">Manba qo'shilmagan</div>
          <button class="btn-primary mt-4" @click="openSource()">
            <Plus class="w-4 h-4" /> Birinchi manba
          </button>
        </li>
      </ul>
    </div>

    <!-- ===== Reasons ===== -->
    <div v-if="tab === 'reasons'" class="card">
      <div class="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h2 class="text-base font-semibold text-slate-900 dark:text-slate-100">Yo'qotish sabablari</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Lead nima uchun yo'qoldi — pul yetmaydi, raqib tanladi va h.k.</p>
        </div>
        <button class="btn-primary" @click="openReason()">
          <Plus class="w-4 h-4" /> Yangi sabab
        </button>
      </div>
      <ul class="divide-y divide-slate-100 dark:divide-slate-800">
        <li v-for="r in reasons" :key="r.id"
            class="p-5 flex items-center justify-between gap-4 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300 shrink-0">
              <XIcon class="w-5 h-5" />
            </span>
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">{{ r.name }}</span>
                <span v-if="!r.is_active" class="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 ring-1 ring-slate-200">Faol emas</span>
              </div>
              <div class="text-[11px] text-slate-400 mt-0.5">tartib: {{ r.order_index }}</div>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button class="btn-outline btn-sm" @click="openReason(r)"><Pencil class="w-3.5 h-3.5" /> Tahrirlash</button>
            <button class="icon-btn-danger" @click="deleteReason(r)"><Trash2 class="w-4 h-4" /></button>
          </div>
        </li>
        <li v-if="!reasons.length" class="p-12 text-center">
          <XIcon class="w-8 h-8 text-slate-300 dark:text-slate-700 mx-auto mb-3" />
          <div class="text-sm text-slate-500 dark:text-slate-400">Sabab qo'shilmagan</div>
          <button class="btn-primary mt-4" @click="openReason()">
            <Plus class="w-4 h-4" /> Birinchi sabab
          </button>
        </li>
      </ul>
    </div>
    </template>

    <!-- ===== Modals ===== -->
    <div v-if="editingPipeline" class="modal-backdrop" @click.self="editingPipeline = null">
      <div class="modal-panel max-w-md">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ editingPipeline.id ? 'Tahrirlash' : 'Yangi varonka' }}</h3>
        <div><label class="field-label">Nomi *</label><input v-model="editingPipeline.name" class="input" /></div>
        <div><label class="field-label">Tavsif</label><textarea v-model="editingPipeline.description" class="input" rows="2"></textarea></div>
        <div class="flex flex-wrap gap-4">
          <label class="inline-flex items-center gap-2 text-sm"><input type="checkbox" v-model="editingPipeline.is_default" /> Default</label>
          <label class="inline-flex items-center gap-2 text-sm"><input type="checkbox" v-model="editingPipeline.is_active" /> Faol</label>
        </div>
        <div><label class="field-label">Tartib</label><input v-model.number="editingPipeline.order_index" type="number" class="input" /></div>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="editingPipeline = null">Bekor</button>
          <button class="btn-primary" @click="savePipeline"><Save class="w-4 h-4" /> Saqlash</button>
        </div>
      </div>
    </div>

    <div v-if="editingStage" class="modal-backdrop" @click.self="editingStage = null">
      <div class="modal-panel max-w-md">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ editingStage.id ? 'Tahrirlash' : 'Yangi bosqich' }}</h3>
        <div><label class="field-label">Nomi *</label><input v-model="editingStage.name" class="input" /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="field-label">Tartib</label><input v-model.number="editingStage.order_index" type="number" class="input" /></div>
          <div>
            <label class="field-label">Rang</label>
            <input v-model="editingStage.color" type="color" class="input h-[42px] p-1 cursor-pointer" />
          </div>
        </div>
        <div class="flex flex-wrap gap-4">
          <label class="inline-flex items-center gap-2 text-sm"><input type="checkbox" v-model="editingStage.is_terminal" /> Yakuniy ✓ (konvertatsiya)</label>
          <label class="inline-flex items-center gap-2 text-sm"><input type="checkbox" v-model="editingStage.is_active" /> Faol</label>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="editingStage = null">Bekor</button>
          <button class="btn-primary" @click="saveStage"><Save class="w-4 h-4" /> Saqlash</button>
        </div>
      </div>
    </div>

    <div v-if="editingSource" class="modal-backdrop" @click.self="editingSource = null">
      <div class="modal-panel max-w-md">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ editingSource.id ? 'Tahrirlash' : 'Yangi manba' }}</h3>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="field-label">Kod *</label><input v-model="editingSource.code" class="input font-mono" placeholder="instagram" /></div>
          <div><label class="field-label">Tartib</label><input v-model.number="editingSource.order_index" type="number" class="input" /></div>
        </div>
        <div><label class="field-label">Nomi *</label><input v-model="editingSource.name" class="input" placeholder="Instagram" /></div>
        <label class="inline-flex items-center gap-2 text-sm"><input type="checkbox" v-model="editingSource.is_active" /> Faol</label>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="editingSource = null">Bekor</button>
          <button class="btn-primary" @click="saveSource"><Save class="w-4 h-4" /> Saqlash</button>
        </div>
      </div>
    </div>

    <div v-if="editingReason" class="modal-backdrop" @click.self="editingReason = null">
      <div class="modal-panel max-w-md">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ editingReason.id ? 'Tahrirlash' : 'Yangi sabab' }}</h3>
        <div><label class="field-label">Nomi *</label><input v-model="editingReason.name" class="input" placeholder="Pul yetarli emas" /></div>
        <div><label class="field-label">Tartib</label><input v-model.number="editingReason.order_index" type="number" class="input" /></div>
        <label class="inline-flex items-center gap-2 text-sm"><input type="checkbox" v-model="editingReason.is_active" /> Faol</label>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="editingReason = null">Bekor</button>
          <button class="btn-primary" @click="saveReason"><Save class="w-4 h-4" /> Saqlash</button>
        </div>
      </div>
    </div>
  </div>
</template>
