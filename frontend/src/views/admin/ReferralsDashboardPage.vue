<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Gift, Users, HandCoins, TrendingUp, Download, Search, Filter as FilterIcon,
  X as XIcon, Clock, CheckCircle2, XCircle, Wallet, AlertTriangle, Award,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import {
  referralsApi,
  type ReferralRead, type ReferralStats, type ReferralStatus,
} from '@/api/referrals.api'
import { downloadCsv } from '@/api/http'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const toast = useToast()
const auth = useAuthStore()

const loading = ref(true)
const stats = ref<ReferralStats | null>(null)
const items = ref<ReferralRead[]>([])
const statusFilter = ref<ReferralStatus | ''>('')
const search = ref('')

async function load() {
  loading.value = true
  try {
    const [s, list] = await Promise.all([
      referralsApi.stats(),
      referralsApi.list(statusFilter.value ? { status_filter: statusFilter.value } : {}),
    ])
    stats.value = s
    items.value = list
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(load)

const filtered = computed(() => {
  if (!search.value.trim()) return items.value
  const q = search.value.toLowerCase()
  return items.value.filter(r =>
    (r.referred_full_name || '').toLowerCase().includes(q),
  )
})

function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '0'
  return Math.round(n).toLocaleString('uz-UZ')
}
function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short', year: 'numeric' })
}

const STATUS_LABEL: Record<ReferralStatus, string> = {
  pending: 'Kutilmoqda',
  active: 'Faol',
  spent_on_contract: 'Chegirma',
  paid_cash: "Naqd to'langan",
  cancelled: 'Bekor',
}
function statusTone(s: ReferralStatus): string {
  switch (s) {
    case 'pending':
      return 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300'
    case 'active':
      return 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300'
    case 'spent_on_contract':
      return 'bg-brand-50 text-brand-700 ring-brand-200 dark:bg-brand-500/15 dark:text-brand-300'
    case 'paid_cash':
      return 'bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-500/15 dark:text-violet-300'
    case 'cancelled':
      return 'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-300'
  }
}

const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    await downloadCsv('/referrals/export.csv', {
      status_filter: statusFilter.value || undefined,
    })
    toast.success("CSV yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}

const STATUS_TILES: { key: ReferralStatus | ''; label: string }[] = [
  { key: '',                   label: 'Hammasi' },
  { key: 'pending',             label: 'Kutilmoqda' },
  { key: 'active',              label: 'Faol' },
  { key: 'spent_on_contract',   label: 'Chegirma qilingan' },
  { key: 'paid_cash',           label: "Naqd to'langan" },
  { key: 'cancelled',           label: 'Bekor' },
]

const crumbs = [
  { label: 'Bosh sahifa', to: '/admin' },
  { label: 'Referal dasturi' },
]
</script>

<template>
  <div>
    <PageHeader
      title="Referal dasturi"
      :subtitle="stats ? `Jami ${stats.total_referrals} ta taklif · ${fmtMoney(stats.total_cash_paid)} so'm naqd to'langan` : 'Yuklanmoqda...'"
      :crumbs="crumbs"
    >
      <button v-if="auth.isRootSuperadmin" class="btn-outline" :disabled="exporting" @click="exportCsv">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'CSV' }}
      </button>
    </PageHeader>

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else-if="stats">
      <!-- KPI tiles -->
      <section class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-5">
        <div class="card p-4">
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-500">Jami taklif</span>
            <Users class="w-4 h-4 text-slate-400" />
          </div>
          <div class="text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ stats.total_referrals }}</div>
        </div>
        <div class="card p-4">
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] uppercase tracking-wider font-bold text-emerald-700 dark:text-emerald-300">Faol bonuslar</span>
            <CheckCircle2 class="w-4 h-4 text-emerald-500" />
          </div>
          <div class="text-2xl font-bold tabular-nums text-emerald-700 dark:text-emerald-300">{{ stats.by_status.active || 0 }}</div>
        </div>
        <div class="card p-4">
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] uppercase tracking-wider font-bold text-brand-700 dark:text-brand-300">Chegirma qilingan</span>
            <Gift class="w-4 h-4 text-brand-500" />
          </div>
          <div class="text-xl font-bold tabular-nums text-brand-700 dark:text-brand-300">{{ fmtMoney(stats.total_discount_amount) }} <span class="text-xs font-normal">so'm</span></div>
          <div class="text-[11px] text-slate-500 mt-0.5">{{ stats.by_status.spent_on_contract || 0 }} ta bonus</div>
        </div>
        <div class="card p-4">
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] uppercase tracking-wider font-bold text-violet-700 dark:text-violet-300">Naqd to'langan</span>
            <HandCoins class="w-4 h-4 text-violet-500" />
          </div>
          <div class="text-xl font-bold tabular-nums text-violet-700 dark:text-violet-300">{{ fmtMoney(stats.total_cash_paid) }} <span class="text-xs font-normal">so'm</span></div>
          <div class="text-[11px] text-slate-500 mt-0.5">{{ stats.by_status.paid_cash || 0 }} ta bonus</div>
        </div>
      </section>

      <!-- Pending cash payouts banner -->
      <RouterLink v-if="stats.cash_pending_count > 0"
                  to="/accountant/referral-payouts"
                  class="card p-4 mb-5 flex items-center gap-3 hover:shadow-md transition border-l-4 border-amber-400">
        <span class="grid place-items-center w-10 h-10 rounded-xl bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300 shrink-0">
          <AlertTriangle class="w-5 h-5" />
        </span>
        <div class="flex-1 min-w-0">
          <div class="font-semibold text-slate-900 dark:text-slate-100">
            {{ stats.cash_pending_count }} ta naqd to'lov so'rovi navbatda
          </div>
          <div class="text-xs text-slate-600 dark:text-slate-400">
            Umumiy summasi: <strong>{{ fmtMoney(stats.cash_pending_amount) }} so'm</strong> · Buxgalter tomonidan tasdiqlanmoqda
          </div>
        </div>
        <span class="text-xs font-semibold text-brand-600 dark:text-brand-300">Ko'rish →</span>
      </RouterLink>

      <!-- Top referrers -->
      <section class="card overflow-hidden mb-5">
        <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
            <Award class="w-4 h-4" />
          </span>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Top tavsiya qiluvchilar</h2>
        </div>
        <div v-if="!stats.top_referrers.length" class="p-10">
          <EmptyState :icon="Award" title="Hali tavsiya qiluvchilar yo'q" subtitle="Birinchi referal'ni kuting" />
        </div>
        <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800/60">
          <li v-for="(r, idx) in stats.top_referrers" :key="r.user_id" class="p-4 flex items-center gap-3">
            <span class="grid place-items-center w-9 h-9 rounded-xl shrink-0 text-sm font-bold"
                  :class="idx === 0 ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300'
                       : idx === 1 ? 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'
                       : idx === 2 ? 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300'
                       : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'">
              #{{ idx + 1 }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-slate-900 dark:text-slate-100 truncate">{{ r.full_name || '—' }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <span v-if="r.phone" class="font-mono">{{ r.phone }}</span>
                <span v-if="r.referral_code" class="text-slate-400">·</span>
                <span v-if="r.referral_code" class="font-mono">{{ r.referral_code }}</span>
              </div>
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mt-1 flex flex-wrap gap-2">
                <span>Faol: <strong>{{ r.active_count }}</strong></span>
                <span>Chegirma: <strong>{{ r.spent_count }}</strong></span>
                <span>Naqd: <strong>{{ r.paid_count }}</strong></span>
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ r.total_invited }}</div>
              <div class="text-[10px] text-slate-500">ta taklif</div>
              <div class="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">
                +{{ fmtMoney(r.earned_amount) }} so'm
              </div>
            </div>
          </li>
        </ul>
      </section>

      <!-- Status quick-tabs -->
      <div class="flex flex-wrap gap-2 mb-3">
        <button v-for="t in STATUS_TILES" :key="t.key || 'all'" type="button"
                class="text-xs px-3 py-1.5 rounded-lg border transition"
                :class="statusFilter === t.key
                  ? 'border-brand-300 bg-brand-50 dark:bg-brand-500/15 text-brand-700 dark:text-brand-300'
                  : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'"
                @click="statusFilter = t.key; load()">
          {{ t.label }}<span v-if="t.key" class="ml-1 opacity-60">({{ stats.by_status[t.key] || 0 }})</span>
        </button>
      </div>

      <!-- Search -->
      <div class="card p-3 mb-4 flex flex-wrap items-center gap-2">
        <div class="relative flex-1 min-w-[200px]">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input v-model="search" class="input pl-10" placeholder="Taklif qilingan abituriyent F.I.Sh." />
        </div>
        <button v-if="search" class="btn-ghost text-xs" @click="search = ''">
          <XIcon class="w-3 h-3" /> Tozalash
        </button>
      </div>

      <!-- Referrals list -->
      <div v-if="!filtered.length" class="card p-6">
        <EmptyState :icon="Gift" title="Referrallar topilmadi" subtitle="Boshqa filter ko'ring" />
      </div>
      <div v-else class="card overflow-hidden">
        <ul class="divide-y divide-slate-100 dark:divide-slate-800/60">
          <li v-for="r in filtered" :key="r.id" class="p-4 flex items-center gap-3">
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-slate-900 dark:text-slate-100 truncate">
                {{ r.referred_full_name || '—' }}
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Yaratilgan: {{ fmtDate(r.created_at) }}
                <span v-if="r.activated_at" class="text-emerald-600 dark:text-emerald-400">· Faol: {{ fmtDate(r.activated_at) }}</span>
                <span v-if="r.payout_at"> · To'landi: {{ fmtDate(r.payout_at) }}</span>
              </div>
            </div>
            <div class="text-right shrink-0">
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1"
                    :class="statusTone(r.status)">
                {{ STATUS_LABEL[r.status] }}
              </span>
              <div class="mt-1 text-xs font-bold tabular-nums text-slate-900 dark:text-slate-100">
                {{ fmtMoney(r.reward_amount) }} <span class="font-normal text-slate-500">so'm</span>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
