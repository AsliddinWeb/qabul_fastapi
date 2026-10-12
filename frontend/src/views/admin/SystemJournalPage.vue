<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  ScrollText, Download, ChevronDown, CalendarDays, Users as UsersIcon,
  Search, UserPlus, FileText, RefreshCw, FileSignature, FileCheck2, FileX, ArrowRight,
} from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import DateRangeFilter from '@/components/ui/DateRangeFilter.vue'
import Pagination from '@/components/ui/Pagination.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { journalApi, type JournalCode, type JournalItem } from '@/api/journal.api'
import { useToast } from '@/composables/useToast'

const toast = useToast()

const EVENTS: { code: JournalCode; label: string; icon: any; tone: string }[] = [
  { code: 'registered',            label: "Ro'yxatdan o'tdi",        icon: UserPlus,       tone: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
  { code: 'registered_by_staff',   label: "Ro'yxatdan o'tkazildi",   icon: UserPlus,       tone: 'bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300' },
  { code: 'application_submitted', label: 'Ariza topshirildi',       icon: FileText,       tone: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300' },
  { code: 'status_changed',        label: "Ariza holati o'zgardi",   icon: ArrowRight, tone: 'bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300' },
  { code: 'contract_created',      label: 'Shartnoma olindi',        icon: FileSignature,  tone: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300' },
  { code: 'contract_renewed',      label: 'Shartnoma yangilandi',    icon: RefreshCw,      tone: 'bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300' },
  { code: 'contract_signed',       label: 'Shartnoma imzolandi',     icon: FileCheck2,     tone: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' },
  { code: 'contract_cancelled',    label: 'Shartnoma bekor qilindi', icon: FileX,         tone: 'bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300' },
]
const EVENT_BY_CODE = Object.fromEntries(EVENTS.map((e) => [e.code, e])) as Record<JournalCode, typeof EVENTS[number]>

const filters = reactive({
  date_from: '',
  date_to: '',
  search: '',
  codes: [] as JournalCode[],
  page: 1,
  size: 50,
})

const items = ref<JournalItem[]>([])
const total = ref(0)
const stats = ref<Partial<Record<JournalCode, number>>>({})
const loading = ref(true)

function apiParams() {
  return {
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
    search: filters.search.trim() || undefined,
    codes: filters.codes.length ? filters.codes.join(',') : undefined,
  }
}

let reqId = 0
async function load() {
  const id = ++reqId
  loading.value = true
  try {
    const res = await journalApi.list({ ...apiParams(), page: filters.page, size: filters.size })
    if (id !== reqId) return
    items.value = res.items
    total.value = res.total
    stats.value = res.stats
  } catch {
    if (id === reqId) toast.error("Daftarni yuklab bo'lmadi")
  } finally {
    if (id === reqId) loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(() => filters.search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { filters.page = 1; load() }, 350)
})
watch(() => [filters.date_from, filters.date_to, filters.codes.join(',')], () => {
  filters.page = 1
  load()
})
watch(() => filters.page, load)
onMounted(load)

function toggleCode(c: JournalCode) {
  const i = filters.codes.indexOf(c)
  if (i >= 0) filters.codes.splice(i, 1)
  else filters.codes.push(c)
}

const lastPage = computed(() => Math.max(1, Math.ceil(total.value / filters.size)))
const statTotal = computed(() => Object.values(stats.value).reduce((a, b) => a + (b || 0), 0))

const exporting = ref<'' | 'dates' | 'applicants'>('')
async function exportXlsx(view: 'dates' | 'applicants') {
  if (exporting.value) return
  exporting.value = view
  try {
    await journalApi.exportXlsx(view, apiParams())
    toast.success('Excel yuklab olindi')
  } catch {
    toast.error("Eksport qilib bo'lmadi")
  } finally {
    exporting.value = ''
  }
}

function fmtDate(iso: string) {
  // Backend already returns Tashkent local time (naive ISO) — show as-is.
  const [d, t] = iso.split('T')
  const [y, m, day] = d.split('-')
  return { date: `${day}.${m}.${y}`, time: (t || '').slice(0, 5) }
}
</script>

<template>
  <div>
    <PageHeader
      title="Tizim daftari"
      subtitle="Abituriyentning ro'yxatdan o'tishidan shartnoma olish va yangilashigacha bo'lgan yo'li."
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Qabul jarayoni' }]"
    >
      <Dropdown align="right" :width="300">
        <template #trigger="{ open }">
          <button class="btn-primary" :disabled="!!exporting">
            <Download class="w-4 h-4" />
            {{ exporting ? 'Tayyorlanmoqda...' : 'Excel yuklab olish' }}
            <ChevronDown class="w-4 h-4 transition-transform" :class="open ? 'rotate-180' : ''" />
          </button>
        </template>
        <button class="menu-item !items-start !py-2.5" @click="exportXlsx('dates')">
          <CalendarDays class="w-4 h-4 text-brand-600 mt-0.5 shrink-0" />
          <span class="text-left">
            <span class="block font-semibold">Sanalar kesimida</span>
            <span class="block text-[11px] text-slate-500 dark:text-slate-400 font-normal leading-snug">
              Har kun bo'yicha hodisalar + kunlik xulosa
            </span>
          </span>
        </button>
        <button class="menu-item !items-start !py-2.5" @click="exportXlsx('applicants')">
          <UsersIcon class="w-4 h-4 text-violet-600 mt-0.5 shrink-0" />
          <span class="text-left">
            <span class="block font-semibold">Abituriyentlar kesimida</span>
            <span class="block text-[11px] text-slate-500 dark:text-slate-400 font-normal leading-snug">
              Har bir abituriyentning to'liq yo'li + xulosa jadvali
            </span>
          </span>
        </button>
      </Dropdown>
    </PageHeader>

    <!-- Filters -->
    <div class="card p-4 mb-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
      <DateRangeFilter v-model:from="filters.date_from" v-model:to="filters.date_to" />
      <div class="lg:col-span-2">
        <label class="field-label">Qidirish</label>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input v-model="filters.search" class="input pl-10"
                 placeholder="F.I.O, JSHSHIR, telefon, passport, ariza yoki shartnoma raqami..." />
        </div>
      </div>
    </div>

    <!-- Event-type chips (counts for the current period/search) -->
    <div class="flex flex-wrap gap-2 mb-4">
      <button v-for="e in EVENTS" :key="e.code" type="button"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold ring-1 transition"
              :class="filters.codes.includes(e.code)
                ? 'bg-brand-600 text-white ring-brand-600'
                : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800'"
              @click="toggleCode(e.code)">
        <component :is="e.icon" class="w-3.5 h-3.5" />
        {{ e.label }}
        <span class="px-1.5 rounded-md text-[10px]"
              :class="filters.codes.includes(e.code) ? 'bg-white/20' : 'bg-slate-100 dark:bg-slate-800'">
          {{ stats[e.code] ?? 0 }}
        </span>
      </button>
      <span class="ml-auto self-center text-xs text-slate-500 dark:text-slate-400">
        Jami hodisalar: <b class="text-slate-700 dark:text-slate-200">{{ statTotal }}</b>
      </span>
    </div>

    <Skeleton v-if="loading && !items.length" type="table" />

    <div v-else-if="!items.length" class="card p-6">
      <EmptyState :icon="ScrollText" title="Hodisalar topilmadi" subtitle="Sana oralig'ini yoki filtrlarni o'zgartirib ko'ring" />
    </div>

    <div v-else class="card overflow-hidden" :class="loading ? 'opacity-60' : ''">
      <div class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th class="w-28">Sana</th>
              <th>Abituriyent</th>
              <th>Hodisa</th>
              <th>Tafsilot</th>
              <th>Kim tomonidan</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(it, i) in items" :key="i">
              <td class="whitespace-nowrap">
                <div class="font-medium text-slate-800 dark:text-slate-200">{{ fmtDate(it.at).date }}</div>
                <div class="text-[11px] text-slate-500">{{ fmtDate(it.at).time }}</div>
              </td>
              <td class="min-w-[200px]">
                <div class="font-medium text-slate-900 dark:text-slate-100">{{ it.full_name }}</div>
                <div class="text-[11px] text-slate-500 font-mono">{{ it.pinfl || '—' }} · {{ it.phone }}</div>
              </td>
              <td class="whitespace-nowrap">
                <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-semibold"
                      :class="EVENT_BY_CODE[it.code]?.tone">
                  <component :is="EVENT_BY_CODE[it.code]?.icon" class="w-3.5 h-3.5" />
                  {{ it.event }}
                </span>
              </td>
              <td class="text-sm text-slate-700 dark:text-slate-300 min-w-[240px]">
                {{ it.detail }}
                <div v-if="it.program && it.code !== 'application_submitted'" class="text-[11px] text-slate-500">{{ it.program }}</div>
              </td>
              <td class="text-sm text-slate-600 dark:text-slate-400 whitespace-nowrap">{{ it.actor || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination v-model:page="filters.page" :last-page="lastPage" :total="total" :size="filters.size" />
    </div>
  </div>
</template>
