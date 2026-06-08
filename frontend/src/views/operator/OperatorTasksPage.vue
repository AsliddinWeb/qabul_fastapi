<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  Phone, Send, Clock, Target, AlertTriangle, RefreshCcw, Search,
  CalendarDays, ArrowRight, CheckCircle2,
} from 'lucide-vue-next'
import { leadsApi, type Lead } from '@/api/leads.api'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { formatPhone } from '@/utils/validators'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()
const meId = computed(() => auth.user?.id || '')

const allLeads = ref<Lead[]>([])
const loading = ref(true)
const refreshing = ref(false)
const lastRefreshAt = ref<Date | null>(null)
const search = ref('')

async function fetchTasks(showSpinner = true) {
  if (showSpinner) refreshing.value = true
  try {
    // Backend caps `size` at 200, so we page through results — most
    // operators stay well under that, but we keep looping until we've
    // pulled every open lead with a scheduled callback. Stop conditions:
    // empty page, smaller-than-max page (last page), or a hard safety
    // ceiling at 1000 rows (5 round-trips).
    const PAGE_SIZE = 200
    const MAX_ROWS = 1000
    const out: Lead[] = []
    let page = 1
    while (out.length < MAX_ROWS) {
      const r = await leadsApi.list({
        assigned_to_id: meId.value,
        status: 'open',
        page,
        size: PAGE_SIZE,
      })
      const items = r.items || []
      out.push(...items.filter(l => !!l.next_contact_at))
      if (items.length < PAGE_SIZE) break  // last page
      page += 1
    }
    allLeads.value = out
    lastRefreshAt.value = new Date()
  } catch {
    toast.error("Vazifalarni yuklab bo'lmadi")
  } finally {
    refreshing.value = false
    loading.value = false
  }
}

onMounted(() => {
  fetchTasks(false)
})
// Auto-refresh every 60s so newly scheduled callbacks land without a
// manual refresh, same cadence as the dashboard widget.
const pollId = window.setInterval(() => fetchTasks(false), 60_000)
onUnmounted(() => window.clearInterval(pollId))

// ---------- Filtering + grouping ----------
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return allLeads.value
  return allLeads.value.filter(l =>
    (l.full_name || '').toLowerCase().includes(q) ||
    (l.phone || '').replace(/\D/g, '').includes(q.replace(/\D/g, '')) ||
    (l.next_contact_note || '').toLowerCase().includes(q),
  )
})

interface Bucket {
  key: 'overdue' | 'today' | 'tomorrow' | 'week' | 'later'
  label: string
  tone: 'rose' | 'amber' | 'sky' | 'violet' | 'slate'
  leads: Lead[]
}

const buckets = computed<Bucket[]>(() => {
  const now = new Date()
  const startOfToday = new Date(now); startOfToday.setHours(0, 0, 0, 0)
  const endOfToday = new Date(startOfToday); endOfToday.setHours(23, 59, 59, 999)
  const startOfTomorrow = new Date(startOfToday); startOfTomorrow.setDate(startOfTomorrow.getDate() + 1)
  const endOfTomorrow = new Date(endOfToday); endOfTomorrow.setDate(endOfTomorrow.getDate() + 1)
  const endOfWeek = new Date(endOfToday); endOfWeek.setDate(endOfWeek.getDate() + 7)

  const out: Record<Bucket['key'], Lead[]> = {
    overdue: [], today: [], tomorrow: [], week: [], later: [],
  }
  for (const l of filtered.value) {
    const t = new Date(l.next_contact_at!).getTime()
    if (t < now.getTime()) out.overdue.push(l)
    else if (t <= endOfToday.getTime()) out.today.push(l)
    else if (t <= endOfTomorrow.getTime()) out.tomorrow.push(l)
    else if (t <= endOfWeek.getTime()) out.week.push(l)
    else out.later.push(l)
  }
  // Within each bucket, sort by time so the soonest callback is on top.
  for (const k of Object.keys(out) as Bucket['key'][]) {
    out[k].sort((a, b) =>
      new Date(a.next_contact_at!).getTime() - new Date(b.next_contact_at!).getTime(),
    )
  }
  return [
    { key: 'overdue',  label: "Muddati o'tgan", tone: 'rose',  leads: out.overdue },
    { key: 'today',    label: 'Bugun',          tone: 'amber', leads: out.today },
    { key: 'tomorrow', label: 'Ertaga',         tone: 'sky',   leads: out.tomorrow },
    { key: 'week',     label: 'Keyingi 7 kun',  tone: 'violet', leads: out.week },
    { key: 'later',    label: 'Keyinroq',       tone: 'slate', leads: out.later },
  ]
})

const stats = computed(() => ({
  total: filtered.value.length,
  overdue: buckets.value[0].leads.length,
  today: buckets.value[1].leads.length,
  upcoming: buckets.value[2].leads.length + buckets.value[3].leads.length + buckets.value[4].leads.length,
}))

// ---------- Visual helpers ----------
function fmtTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })
  }
  const tomorrow = new Date(now); tomorrow.setDate(now.getDate() + 1)
  if (d.toDateString() === tomorrow.toDateString()) {
    return 'Ertaga ' + d.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleString('uz-UZ', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
function relTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const past = ms > 0
  const abs = Math.abs(ms)
  if (abs < 60_000) return past ? 'hozir' : 'hozir'
  if (abs < 3_600_000) {
    const m = Math.floor(abs / 60_000)
    return past ? `${m} daq oldin` : `${m} daq keyin`
  }
  if (abs < 86_400_000) {
    const h = Math.floor(abs / 3_600_000)
    return past ? `${h} soat oldin` : `${h} soat keyin`
  }
  const d = Math.floor(abs / 86_400_000)
  return past ? `${d} kun oldin` : `${d} kun keyin`
}

const TONE_BG: Record<Bucket['tone'], string> = {
  rose:   'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300',
  amber:  'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
  sky:    'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300',
  violet: 'bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300',
  slate:  'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}
const TONE_RING: Record<Bucket['tone'], string> = {
  rose:   'ring-rose-200/70 dark:ring-rose-700/30',
  amber:  'ring-amber-200/70 dark:ring-amber-700/30',
  sky:    'ring-sky-200/70 dark:ring-sky-700/30',
  violet: 'ring-violet-200/70 dark:ring-violet-700/30',
  slate:  'ring-slate-200/70 dark:ring-slate-700/30',
}

function fmtLastRefresh(): string {
  if (!lastRefreshAt.value) return ''
  return lastRefreshAt.value.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div>
    <PageHeader title="Vazifalarim"
                subtitle="Rejalashtirilgan qo'ng'iroqlar va aloqalar. Yangi vazifa qo'shish uchun lead detail sahifasidan 'Keyingi aloqa'ni o'rnating.">
      <span v-if="lastRefreshAt" class="hidden sm:inline text-[11px] text-slate-400 dark:text-slate-500">
        {{ fmtLastRefresh() }} da yangilandi
      </span>
      <button type="button"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition disabled:opacity-50"
              :disabled="refreshing"
              @click="fetchTasks()">
        <RefreshCcw class="w-3 h-3" :class="{ 'animate-spin': refreshing }" />
        Yangilash
      </button>
    </PageHeader>

    <!-- Stats tiles -->
    <section v-if="!loading" class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
      <StatCard label="Jami" :value="stats.total" :icon="Target" tone="violet" />
      <StatCard label="Muddati o'tgan" :value="stats.overdue" :icon="AlertTriangle" tone="rose"
                :hint="stats.overdue ? `darhol bog'laning` : undefined" />
      <StatCard label="Bugun" :value="stats.today" :icon="CalendarDays" tone="amber" />
      <StatCard label="Kelajakda" :value="stats.upcoming" :icon="Clock" tone="sky" />
    </section>

    <!-- Search bar -->
    <section class="card p-3 mb-5">
      <div class="relative">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        <input v-model="search" class="input pl-10"
               placeholder="F.I.Sh., telefon yoki izoh bo'yicha qidirish..." />
      </div>
    </section>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <Skeleton class="h-32" />
      <Skeleton class="h-32" />
    </div>

    <!-- Empty -->
    <div v-else-if="!filtered.length" class="card p-6">
      <EmptyState :icon="CheckCircle2" title="Rejalashtirilgan vazifa yo'q"
                  subtitle="Lead detail sahifasida 'Keyingi aloqa' o'rnating — bu yerda ko'rinadi" />
    </div>

    <!-- Bucketed list -->
    <div v-else class="space-y-5">
      <template v-for="b in buckets" :key="b.key">
        <section v-if="b.leads.length" class="card overflow-hidden">
          <div class="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-3">
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="grid place-items-center w-8 h-8 rounded-lg text-xs font-bold tabular-nums"
                    :class="TONE_BG[b.tone]">
                {{ b.leads.length }}
              </span>
              <h2 class="text-sm font-semibold text-slate-900 dark:text-slate-100">{{ b.label }}</h2>
            </div>
          </div>

          <ul class="divide-y divide-slate-100 dark:divide-slate-800/60">
            <li v-for="l in b.leads" :key="l.id"
                class="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors flex items-start gap-3">
              <!-- Time pill -->
              <div class="shrink-0">
                <div class="min-w-[5rem] px-3 py-2 rounded-xl ring-1 text-center leading-tight"
                     :class="[TONE_BG[b.tone], TONE_RING[b.tone]]">
                  <div class="text-[12px] font-bold tabular-nums">{{ fmtTime(l.next_contact_at!) }}</div>
                  <div class="text-[10px] opacity-80 mt-0.5">{{ relTime(l.next_contact_at!) }}</div>
                </div>
              </div>

              <!-- Identity + note -->
              <RouterLink :to="`/operator/leads/${l.id}`" class="flex-1 min-w-0 group">
                <div class="font-semibold text-slate-900 dark:text-slate-100 truncate group-hover:text-brand-700 dark:group-hover:text-brand-300 transition">
                  {{ l.full_name }}
                </div>
                <div class="mt-0.5 flex items-center gap-3 text-[12px] text-slate-500 dark:text-slate-400 flex-wrap">
                  <span class="font-mono inline-flex items-center gap-1">
                    <Phone class="w-3 h-3" /> {{ formatPhone(l.phone) }}
                  </span>
                  <span v-if="l.stage_name" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    {{ l.stage_name }}
                  </span>
                </div>
                <div v-if="l.next_contact_note" class="mt-1.5 text-[12px] text-slate-600 dark:text-slate-400 italic line-clamp-2">
                  «{{ l.next_contact_note }}»
                </div>
              </RouterLink>

              <!-- Actions -->
              <div class="flex items-center gap-1.5 shrink-0">
                <a :href="`tel:${l.phone}`"
                   class="grid place-items-center w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-300 dark:hover:bg-emerald-500/25 transition"
                   title="Qo'ng'iroq qilish">
                  <Phone class="w-4 h-4" />
                </a>
                <a v-if="l.telegram_username"
                   :href="`https://t.me/${l.telegram_username}`" target="_blank" rel="noopener"
                   class="grid place-items-center w-9 h-9 rounded-lg bg-sky-50 text-sky-600 hover:bg-sky-100 dark:bg-sky-500/15 dark:text-sky-300 dark:hover:bg-sky-500/25 transition"
                   title="Telegram">
                  <Send class="w-4 h-4" />
                </a>
                <button type="button"
                        class="hidden sm:grid place-items-center w-9 h-9 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 transition"
                        title="Lead'ga o'tish"
                        @click="router.push(`/operator/leads/${l.id}`)">
                  <ArrowRight class="w-4 h-4" />
                </button>
              </div>
            </li>
          </ul>
        </section>
      </template>
    </div>
  </div>
</template>
