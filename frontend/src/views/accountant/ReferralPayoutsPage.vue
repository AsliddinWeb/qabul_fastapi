<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  HandCoins, CheckCircle2, XCircle, Clock, AlertTriangle, Search, Filter as FilterIcon,
  X as XIcon, Phone,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { referralsApi, type ReferralPayoutRead } from '@/api/referrals.api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const toast = useToast()
const { ask } = useConfirm()

type StatusFilter = '' | 'requested' | 'approved' | 'paid' | 'rejected'

const items = ref<ReferralPayoutRead[]>([])
const loading = ref(false)
const statusFilter = ref<StatusFilter>('requested')
const search = ref('')

async function load() {
  loading.value = true
  try {
    items.value = await referralsApi.payouts(statusFilter.value || undefined)
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
  return items.value.filter(p =>
    (p.referrer_full_name || '').toLowerCase().includes(q) ||
    (p.referrer_phone || '').toLowerCase().includes(q),
  )
})

const counts = computed(() => {
  const out = { requested: 0, approved: 0, paid: 0, rejected: 0 }
  for (const p of items.value) out[p.status]++
  return out
})

async function approve(p: ReferralPayoutRead) {
  const ok = await ask({
    title: "So'rovni tasdiqlash",
    message: `${p.referrer_full_name || p.referrer_phone}'ga ${fmtMoney(p.amount)} so'm to'lov so'rovini tasdiqlaysizmi?`,
    confirmLabel: 'Tasdiqlash',
    tone: 'primary',
  })
  if (!ok) return
  try {
    await referralsApi.approvePayout(p.id)
    toast.success('Tasdiqlandi')
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || 'Xatolik')
  }
}

async function pay(p: ReferralPayoutRead) {
  const ok = await ask({
    title: "To'langan deb belgilash",
    message: `${p.referrer_full_name || p.referrer_phone}'ga ${fmtMoney(p.amount)} so'm naqd berildi deb belgilaysizmi? Bu amalni bekor qilib bo'lmaydi.`,
    confirmLabel: "To'langan",
    tone: 'primary',
  })
  if (!ok) return
  try {
    await referralsApi.payPayout(p.id)
    toast.success("Belgilandi: to'langan")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || 'Xatolik')
  }
}

async function reject(p: ReferralPayoutRead) {
  const reason = window.prompt('Rad etish sababi:') || ''
  if (!reason.trim()) return
  try {
    await referralsApi.rejectPayout(p.id, reason)
    toast.success('Rad etildi')
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || 'Xatolik')
  }
}

function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '0'
  return Math.round(n).toLocaleString('uz-UZ')
}
function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

const STATUS_LABEL: Record<ReferralPayoutRead['status'], string> = {
  requested: 'Kutilmoqda',
  approved:  'Tasdiqlangan',
  paid:      "To'langan",
  rejected:  'Rad etilgan',
}
const crumbs = [
  { label: 'Bosh sahifa', to: '/accountant' },
  { label: "To'lov so'rovlari" },
]

function statusTone(s: ReferralPayoutRead['status']): string {
  switch (s) {
    case 'requested':
      return 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300'
    case 'approved':
      return 'bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/10 dark:text-sky-300'
    case 'paid':
      return 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300'
    case 'rejected':
      return 'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-300'
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Referal to'lov so'rovlari"
      subtitle="Abituriyentlarning naqd pul olish so'rovlari"
      :crumbs="crumbs"
    />

    <!-- Quick status tabs -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
      <button v-for="s in (['requested', 'approved', 'paid', 'rejected'] as const)" :key="s"
              class="text-left rounded-xl px-3 py-2.5 border bg-white dark:bg-slate-900 hover:shadow-sm transition"
              :class="statusFilter === s ? 'border-brand-300 ring-2 ring-brand-200/60 dark:border-brand-600 dark:ring-brand-700/30' : 'border-slate-200/70 dark:border-slate-800'"
              @click="statusFilter = s; load()">
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500">{{ STATUS_LABEL[s] }}</div>
        <div class="mt-1 text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ counts[s] || 0 }}</div>
      </button>
    </div>

    <!-- Search -->
    <div class="card p-3 mb-4 flex flex-wrap items-center gap-2">
      <div class="relative flex-1 min-w-[200px]">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        <input v-model="search" class="input pl-10" placeholder="F.I.Sh. yoki telefon" />
      </div>
      <button v-if="search || statusFilter !== ''" class="btn-ghost text-xs" @click="search = ''; statusFilter = ''; load()">
        <XIcon class="w-3 h-3" /> Tozalash
      </button>
    </div>

    <Skeleton v-if="loading" type="table" />
    <div v-else-if="!filtered.length" class="card p-6">
      <EmptyState :icon="HandCoins" title="So'rovlar topilmadi" subtitle="Boshqa filter ko'ring" />
    </div>

    <ul v-else class="space-y-2.5">
      <li v-for="p in filtered" :key="p.id" class="card p-4 flex flex-wrap items-center gap-3">
        <span class="grid place-items-center w-10 h-10 rounded-xl ring-1"
              :class="statusTone(p.status)">
          <HandCoins v-if="p.status === 'paid'" class="w-4 h-4" />
          <Clock v-else-if="p.status === 'requested'" class="w-4 h-4" />
          <CheckCircle2 v-else-if="p.status === 'approved'" class="w-4 h-4" />
          <XCircle v-else class="w-4 h-4" />
        </span>
        <div class="flex-1 min-w-0">
          <div class="font-semibold text-slate-900 dark:text-slate-100 truncate">
            {{ p.referrer_full_name || '—' }}
          </div>
          <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5">
            <span v-if="p.referrer_phone" class="inline-flex items-center gap-1 font-mono">
              <Phone class="w-3 h-3" /> {{ p.referrer_phone }}
            </span>
            <span class="inline-flex items-center gap-1">
              <Clock class="w-3 h-3" /> {{ fmtDate(p.created_at) }}
            </span>
            <span v-if="p.paid_at" class="text-emerald-600 dark:text-emerald-400">
              · To'langan: {{ fmtDate(p.paid_at) }}
            </span>
          </div>
          <p v-if="p.notes" class="text-xs text-slate-600 dark:text-slate-400 mt-1 italic">{{ p.notes }}</p>
          <p v-if="p.rejected_reason" class="text-xs text-rose-600 dark:text-rose-400 mt-1">
            Sabab: {{ p.rejected_reason }}
          </p>
        </div>
        <div class="text-right shrink-0">
          <div class="font-bold tabular-nums text-slate-900 dark:text-slate-100">
            {{ fmtMoney(p.amount) }} <span class="text-xs font-normal text-slate-500">so'm</span>
          </div>
          <div class="text-[10px] text-slate-400">{{ p.referral_count }} ta bonus</div>
          <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1 mt-1"
                :class="statusTone(p.status)">
            {{ STATUS_LABEL[p.status] }}
          </span>
        </div>
        <div class="basis-full flex flex-wrap justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800"
             v-if="p.status === 'requested' || p.status === 'approved'">
          <button v-if="p.status === 'requested'" class="btn-outline btn-sm text-sky-600 dark:text-sky-300"
                  @click="approve(p)">
            <CheckCircle2 class="w-3.5 h-3.5" /> Tasdiqlash
          </button>
          <button class="btn-outline btn-sm text-emerald-600 dark:text-emerald-300" @click="pay(p)">
            <HandCoins class="w-3.5 h-3.5" /> To'langan
          </button>
          <button class="btn-outline btn-sm text-rose-600 dark:text-rose-300" @click="reject(p)">
            <XCircle class="w-3.5 h-3.5" /> Rad
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>
