<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { AxiosError } from 'axios'
import { Check, Search, X, GraduationCap, Filter as FilterIcon } from 'lucide-vue-next'
import { programsApi, type ProgramRead } from '@/api/programs.api'
import { applicationsApi, type ApplicationDetailed } from '@/api/applications.api'
import Skeleton from '@/components/ui/Skeleton.vue'

const programs = ref<ProgramRead[]>([])
const myApps = ref<ApplicationDetailed[]>([])
const loading = ref(true)
const submitting = ref<string | null>(null)
const message = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

// Filter state
const search = ref('')
const branchFilter = ref('')
const levelFilter = ref('')
const formFilter = ref('')
const visibleCount = ref(12)

const appliedProgramIds = computed(
  () => new Set(myApps.value.map((a) => a.program_id)),
)

// Build distinct option lists from the loaded programs (no extra requests)
const branches = computed(() => {
  const m = new Map<string, string>()
  for (const p of programs.value) {
    if (p.branch_id && p.branch_name) m.set(p.branch_id, p.branch_name)
  }
  return Array.from(m.entries()).map(([id, name]) => ({ id, name }))
})
const levels = computed(() => {
  const m = new Map<string, string>()
  for (const p of programs.value) {
    if (p.education_level_id && p.education_level_name) m.set(p.education_level_id, p.education_level_name)
  }
  return Array.from(m.entries()).map(([id, name]) => ({ id, name }))
})
const forms = computed(() => {
  const m = new Map<string, string>()
  for (const p of programs.value) {
    if (p.education_form_id && p.education_form_name) m.set(p.education_form_id, p.education_form_name)
  }
  return Array.from(m.entries()).map(([id, name]) => ({ id, name }))
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return programs.value.filter((p) => {
    if (branchFilter.value && p.branch_id !== branchFilter.value) return false
    if (levelFilter.value && p.education_level_id !== levelFilter.value) return false
    if (formFilter.value && p.education_form_id !== formFilter.value) return false
    if (q) {
      const hay = `${p.name} ${p.code} ${p.branch_name || ''}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
})

const visiblePrograms = computed(() => filtered.value.slice(0, visibleCount.value))

const activeFilterCount = computed(() => {
  let n = 0
  if (search.value.trim()) n++
  if (branchFilter.value) n++
  if (levelFilter.value) n++
  if (formFilter.value) n++
  return n
})

watch([search, branchFilter, levelFilter, formFilter], () => { visibleCount.value = 12 })

function clearFilters() {
  search.value = ''
  branchFilter.value = ''
  levelFilter.value = ''
  formFilter.value = ''
}

function fmtPrice(v: number | string | null | undefined): string {
  if (!v) return '—'
  const n = typeof v === 'string' ? parseFloat(v) : Number(v)
  if (!n || isNaN(n)) return '—'
  return Math.floor(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}

onMounted(async () => {
  try {
    const [progs, apps] = await Promise.all([
      programsApi.list({ active_only: true }),
      applicationsApi.myList().catch(() => []),
    ])
    programs.value = progs
    myApps.value = apps
  } finally {
    loading.value = false
  }
})

async function apply(p: ProgramRead) {
  submitting.value = p.id
  message.value = null
  try {
    await applicationsApi.submit({
      admission_type: 'yangi_qabul',
      branch_id: p.branch_id,
      education_level_id: p.education_level_id,
      education_form_id: p.education_form_id,
      program_id: p.id,
    })
    message.value = { type: 'ok', text: 'Ariza yuborildi' }
    myApps.value = await applicationsApi.myList()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    message.value = {
      type: 'err',
      text: ax.response?.data?.error?.message || "Ariza yuborib bo'lmadi",
    }
  } finally {
    submitting.value = null
  }
}
</script>

<template>
  <div class="max-w-6xl space-y-5">
    <!-- Header -->
    <div class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Yo'nalishlar</h1>
        <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Joriy o'quv yili uchun mavjud yo'nalishlar.
        </p>
      </div>
      <div v-if="!loading" class="text-sm text-slate-500 dark:text-slate-400 tabular-nums">
        {{ filtered.length }} / {{ programs.length }} ta yo'nalish
      </div>
    </div>

    <!-- Toast -->
    <div v-if="message" class="text-sm rounded-lg p-3 flex items-start justify-between gap-3"
         :class="message.type === 'ok'
           ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
           : 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300'">
      <span>{{ message.text }}</span>
      <button class="opacity-70 hover:opacity-100" @click="message = null">
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Filter bar -->
    <div class="card p-3 sm:p-4 space-y-3">
      <!-- Search row -->
      <div class="flex items-center gap-2">
        <div class="relative flex-1 min-w-0">
          <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            v-model="search"
            type="text"
            class="input pl-10"
            placeholder="Yo'nalish nomi yoki kod..."
          />
        </div>
        <button v-if="activeFilterCount > 0"
                class="btn-ghost btn-sm shrink-0"
                @click="clearFilters">
          <X class="w-3.5 h-3.5" />
          Tozalash
        </button>
      </div>

      <!-- Filter selects -->
      <div class="grid sm:grid-cols-3 gap-2">
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Filial</label>
          <select v-model="branchFilter" class="input">
            <option value="">— Hammasi —</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Daraja</label>
          <select v-model="levelFilter" class="input">
            <option value="">— Hammasi —</option>
            <option v-for="l in levels" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Shakli</label>
          <select v-model="formFilter" class="input">
            <option value="">— Hammasi —</option>
            <option v-for="f in forms" :key="f.id" :value="f.id">{{ f.name }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- States -->
    <Skeleton v-if="loading" type="list" />

    <div v-else-if="!programs.length" class="card p-10 text-center">
      <GraduationCap class="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
      <div class="text-sm text-slate-500 dark:text-slate-400">Hozircha yo'nalishlar mavjud emas</div>
    </div>

    <div v-else-if="!filtered.length" class="card p-10 text-center">
      <FilterIcon class="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
      <div class="text-sm text-slate-500 dark:text-slate-400 mb-3">Filterga mos yo'nalish topilmadi</div>
      <button class="btn-secondary btn-sm" @click="clearFilters">Filterlarni tozalash</button>
    </div>

    <!-- Cards grid -->
    <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="p in visiblePrograms"
        :key="p.id"
        class="card p-5 flex flex-col"
      >
        <div class="text-[11px] text-slate-500 dark:text-slate-400 font-mono">{{ p.code }}</div>
        <h3 class="mt-1 font-semibold text-slate-900 dark:text-slate-100 leading-snug">{{ p.name }}</h3>
        <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ p.branch_name || '' }}</div>

        <div class="mt-3 flex flex-wrap gap-1.5 text-[11px]">
          <span v-if="p.education_level_name"
                class="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 rounded font-medium">
            {{ p.education_level_name }}
          </span>
          <span v-if="p.education_form_name"
                class="px-2 py-0.5 bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 rounded font-medium">
            {{ p.education_form_name }}
          </span>
          <span v-if="(p as any).study_duration_years"
                class="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded font-medium">
            {{ (p as any).study_duration_years }} yil
          </span>
        </div>

        <div class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-end justify-between gap-3">
          <div class="min-w-0">
            <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Yillik to'lov</div>
            <div class="font-bold text-slate-900 dark:text-slate-100 tabular-nums">
              {{ fmtPrice(p.tuition_fee) }}
              <span class="text-xs font-normal text-slate-500">so'm</span>
            </div>
          </div>
        </div>

        <div class="mt-3">
          <button
            v-if="appliedProgramIds.has(p.id)"
            class="btn-ghost w-full justify-center"
            disabled
          >
            <Check class="w-4 h-4" /> Ariza topshirilgan
          </button>
          <button
            v-else
            class="btn-primary w-full justify-center"
            :disabled="submitting === p.id"
            @click="apply(p)"
          >
            {{ submitting === p.id ? 'Yuborilmoqda...' : 'Ariza topshirish' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Pagination "load more" -->
    <div v-if="!loading && filtered.length > visibleCount" class="text-center">
      <button class="btn-secondary" @click="visibleCount += 12">
        Yana {{ filtered.length - visibleCount }} ta ko'rsatish
      </button>
    </div>
  </div>
</template>
