<script setup lang="ts">
/**
 * International admissions — staff list page.
 *
 * Two views: 6-column Kanban (default) and flat table (search-friendly).
 * Stage labels match the public landing page; advancing a row moves it
 * to the next column with one click. Rejected rows fall out of both
 * views; toggle the "Rad etilgan" chip to see them.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { AxiosError } from 'axios'
import {
  Globe, Search, X as XIcon, AlertTriangle, ArrowRight, RotateCcw,
  Filter as FilterIcon, LayoutGrid, List,
} from 'lucide-vue-next'
import {
  internationalApi, STAGE_LABELS, STAGE_TONES,
  type IntlApplicationListItem, type IntlStageCounts,
} from '@/api/international.api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useUrlFilters } from '@/composables/useUrlFilters'
import PageHeader from '@/components/ui/PageHeader.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import StatCard from '@/components/ui/StatCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Pagination from '@/components/ui/Pagination.vue'

const toast = useToast()
const { ask } = useConfirm()

const items = ref<IntlApplicationListItem[]>([])
const total = ref(0)
const stats = ref<IntlStageCounts | null>(null)
const loading = ref(false)

const { filters, clear: clearAllFilters, hasActiveFilters } = useUrlFilters({
  view: 'kanban' as 'kanban' | 'table',
  stage: '' as string,           // '0'..'5' or ''
  country: '' as string,
  rejected: '' as '' | 'yes' | 'no',
  search: '' as string,
  page: 1,
  size: 100,
})

async function load() {
  loading.value = true
  try {
    const [list, st] = await Promise.all([
      internationalApi.list({
        stage: filters.stage ? Number(filters.stage) : undefined,
        country: filters.country || undefined,
        rejected: filters.rejected === 'yes' ? true : filters.rejected === 'no' ? false : undefined,
        search: filters.search.trim() || undefined,
        page: filters.page, size: filters.size,
      }),
      internationalApi.stats().catch(() => null),
    ])
    items.value = list.items
    total.value = list.total
    if (st) stats.value = st
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(load)
let searchT: ReturnType<typeof setTimeout> | null = null
watch(() => filters.search, () => {
  if (searchT) clearTimeout(searchT)
  searchT = setTimeout(() => { filters.page = 1; load() }, 300)
})
watch(() => [filters.stage, filters.country, filters.rejected], () => { filters.page = 1; load() })
watch(() => filters.page, load)

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

// Group items by stage for the Kanban view. Rejected rows are excluded
// from the board unless the rejected filter is "yes".
const byStage = computed(() => {
  const out: Record<number, IntlApplicationListItem[]> = {0:[],1:[],2:[],3:[],4:[],5:[]}
  for (const it of items.value) {
    if (it.rejected && filters.rejected !== 'yes') continue
    if (out[it.stage]) out[it.stage].push(it)
  }
  return out
})

async function advance(it: IntlApplicationListItem) {
  if (it.stage >= 5) return
  try {
    await internationalApi.advance(it.id, 'next')
    toast.success('Keyingi bosqichga o\'tkazildi')
    load()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xato")
  }
}

async function rejectRow(it: IntlApplicationListItem) {
  const reason = window.prompt('Rad etish sababi (ixtiyoriy):') || ''
  const ok = await ask({
    title: "Arizani rad etish",
    message: `${it.full_name} ning arizasi rad etilsinmi?`,
    confirmLabel: "Rad etish", tone: 'danger',
  })
  if (!ok) return
  try {
    await internationalApi.reject(it.id, reason || undefined)
    toast.success('Rad etildi')
    load()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xato")
  }
}

function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join('') || '?'
}
function avatarColor(seed: string): string {
  const palette = ['from-brand-500 to-violet-500','from-emerald-500 to-teal-500','from-amber-500 to-orange-500','from-rose-500 to-pink-500','from-sky-500 to-cyan-500']
  let h = 0
  for (let i = 0; i < seed.length; i++) h = ((h << 5) - h + seed.charCodeAt(i)) | 0
  return palette[Math.abs(h) % palette.length]
}

const COUNTRY_OPTS = [
  'Afghanistan','Bangladesh','Egypt','India','Indonesia','Kazakhstan',
  'Kyrgyzstan','Malaysia','Nigeria','Pakistan','Russia','Tajikistan',
  'Turkey','Turkmenistan','Other',
]
</script>

<template>
  <div class="space-y-5">
    <PageHeader
      title="Xalqaro qabul"
      :subtitle="`Chet ellik talabalar arizalarini boshqarish · Jami ${stats?.total ?? 0}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Xalqaro qabul' }]"
    >
      <!-- View switch (Kanban / Table). Stays in the header on every viewport. -->
      <div class="inline-flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 text-xs font-medium">
        <button class="px-3 py-1.5 rounded-md transition-colors inline-flex items-center gap-1.5"
                :class="filters.view === 'kanban'
                  ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100'
                  : 'text-slate-500 dark:text-slate-400'"
                @click="filters.view = 'kanban'">
          <LayoutGrid class="w-3 h-3" /> Kanban
        </button>
        <button class="px-3 py-1.5 rounded-md transition-colors inline-flex items-center gap-1.5"
                :class="filters.view === 'table'
                  ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-slate-100'
                  : 'text-slate-500 dark:text-slate-400'"
                @click="filters.view = 'table'">
          <List class="w-3 h-3" /> Jadval
        </button>
      </div>
    </PageHeader>

    <!-- KPI strip -->
    <section v-if="stats" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <StatCard label="Jami" :value="stats.total" :icon="Globe" tone="brand" />
      <StatCard label="Yangi" :value="stats.stage_0" :icon="Globe" tone="slate" />
      <StatCard label="Hujjat" :value="stats.stage_1" :icon="Globe" tone="brand" />
      <StatCard label="Shartnoma" :value="stats.stage_3" :icon="Globe" tone="amber" />
      <StatCard label="Qabul" :value="stats.stage_5" :icon="Globe" tone="emerald" />
      <StatCard label="Rad etilgan" :value="stats.rejected" :icon="AlertTriangle" tone="rose" />
    </section>

    <!-- Filter bar -->
    <div class="filter-bar">
      <div class="flex-1 min-w-[240px]">
        <label class="field-label">Qidirish</label>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input v-model="filters.search" class="input pl-10" placeholder="Ism, davlat, pasport, email…" />
        </div>
      </div>
      <div class="min-w-[160px]">
        <label class="field-label">Bosqich</label>
        <select v-model="filters.stage" class="input">
          <option value="">— hammasi —</option>
          <option v-for="(label, i) in STAGE_LABELS" :key="i" :value="String(i)">{{ i+1 }}. {{ label }}</option>
        </select>
      </div>
      <div class="min-w-[160px]">
        <label class="field-label">Davlat</label>
        <select v-model="filters.country" class="input">
          <option value="">— hammasi —</option>
          <option v-for="c in COUNTRY_OPTS" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
      <div class="min-w-[140px]">
        <label class="field-label">Holati</label>
        <select v-model="filters.rejected" class="input">
          <option value="">Aktiv</option>
          <option value="yes">Rad etilgan</option>
          <option value="no">Faqat aktiv</option>
        </select>
      </div>
      <div v-if="hasActiveFilters" class="flex items-end">
        <button class="btn-ghost" @click="clearAllFilters">
          <XIcon class="w-4 h-4" /> Tozalash
        </button>
      </div>
    </div>

    <Skeleton v-if="loading" type="table" />

    <!-- KANBAN -->
    <section v-else-if="filters.view === 'kanban'"
             class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
      <div v-for="(label, s) in STAGE_LABELS" :key="s"
           class="card p-3 sm:p-4 ring-1 ring-slate-100 dark:ring-slate-800 min-h-[120px]">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
            {{ s+1 }}. {{ label }}
          </h3>
          <span class="inline-flex items-center justify-center w-6 h-6 rounded-md text-[10px] font-bold ring-1"
                :class="STAGE_TONES[s]">
            {{ byStage[s].length }}
          </span>
        </div>
        <div class="space-y-2">
          <RouterLink v-for="it in byStage[s]" :key="it.id"
                      :to="`/admin/international-admissions/${it.id}`"
                      class="block p-2.5 rounded-lg ring-1 ring-slate-200 dark:ring-slate-700 hover:ring-brand-300 dark:hover:ring-brand-600 transition bg-white dark:bg-slate-900/60">
            <div class="flex items-center gap-2 mb-1.5">
              <div class="grid place-items-center w-7 h-7 rounded text-white text-[10px] font-bold bg-gradient-to-br shrink-0"
                   :class="avatarColor(it.id)">{{ initials(it.full_name) }}</div>
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{{ it.full_name }}</div>
                <div class="text-[10px] font-mono text-slate-500 dark:text-slate-400">{{ it.ref_number }}</div>
              </div>
            </div>
            <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {{ it.country }} · {{ it.program }}
            </div>
            <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {{ it.faculty_text }}
            </div>
          </RouterLink>
          <div v-if="!byStage[s].length" class="text-center text-[11px] text-slate-400 py-3">—</div>
        </div>
      </div>
    </section>

    <!-- TABLE -->
    <section v-else class="card">
      <div v-if="!items.length" class="p-8">
        <EmptyState :icon="Globe" title="Xalqaro arizalar topilmadi"
                    subtitle="Filtrlarni tozalab qaytadan urinib ko'ring" />
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Abituriyent</th>
            <th class="w-32">Davlat</th>
            <th class="w-40">Dastur / Fakultet</th>
            <th class="w-36">Pasport</th>
            <th class="w-44">Telefon / Email</th>
            <th class="w-36">Bosqich</th>
            <th class="w-44 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.id" class="cursor-pointer"
              @click="$router.push(`/admin/international-admissions/${it.id}`)">
            <td>
              <div class="flex items-center gap-3">
                <div class="grid place-items-center w-9 h-9 rounded-lg text-white text-xs font-bold bg-gradient-to-br shrink-0"
                     :class="avatarColor(it.id)">{{ initials(it.full_name) }}</div>
                <div class="min-w-0">
                  <div class="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">{{ it.full_name }}</div>
                  <div class="text-[10px] font-mono text-slate-500 dark:text-slate-400">{{ it.ref_number }}</div>
                </div>
              </div>
            </td>
            <td class="text-sm text-slate-700 dark:text-slate-300">{{ it.country }}</td>
            <td>
              <div class="text-sm text-slate-700 dark:text-slate-300">{{ it.program }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">{{ it.faculty_text }}</div>
            </td>
            <td class="text-xs font-mono text-slate-600 dark:text-slate-400">{{ it.passport_number }}</td>
            <td>
              <div class="text-xs font-mono text-slate-700 dark:text-slate-300">{{ it.phone }}</div>
              <div class="text-[10px] text-slate-500 dark:text-slate-400 truncate">{{ it.email }}</div>
            </td>
            <td>
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold ring-1"
                    :class="it.rejected
                      ? 'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-700/40'
                      : STAGE_TONES[it.stage]">
                {{ it.rejected ? 'Rad etilgan' : STAGE_LABELS[it.stage] }}
              </span>
            </td>
            <td class="text-right" @click.stop>
              <div class="inline-flex items-center gap-1.5">
                <button v-if="!it.rejected && it.stage < 5"
                        class="btn-outline btn-sm" title="Keyingi bosqich"
                        @click="advance(it)">
                  <ArrowRight class="w-3.5 h-3.5" />
                </button>
                <button v-if="!it.rejected" class="icon-btn-danger" title="Rad etish"
                        @click="rejectRow(it)">
                  <RotateCcw class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <Pagination v-if="items.length" v-model:page="filters.page" :last-page="lastPage()" :total="total" :size="filters.size" />
    </section>
  </div>
</template>
