<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Gift, Copy, Check, Users, Send, Phone, Share2, AlertTriangle, CheckCircle2, Wallet, Clock,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { referralsApi, type ReferralRead, type ReferralStatus, type ReferralCode } from '@/api/referrals.api'
import { useToast } from '@/composables/useToast'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const toast = useToast()

const loading = ref(true)
const code = ref<ReferralCode | null>(null)
const refs = ref<ReferralRead[]>([])
const copied = ref(false)

onMounted(async () => {
  try {
    const [c, r] = await Promise.all([
      referralsApi.myCode(),
      referralsApi.mine(),
    ])
    code.value = c
    refs.value = r
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
})

async function copyLink() {
  if (!code.value) return
  try {
    await navigator.clipboard.writeText(code.value.share_url)
    copied.value = true
    toast.success("Link nusxalandi")
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    toast.error("Brauzer ruxsat bermadi — qo'lda nusxalang")
  }
}

function shareTelegram() {
  if (!code.value) return
  const text = encodeURIComponent(
    `Xalqaro innovatsion universitetga ariza topshirish uchun mening referal linkim orqali o'tib ro'yxatdan o'ting:\n\n${code.value.share_url}`,
  )
  window.open(`https://t.me/share/url?url=${encodeURIComponent(code.value.share_url)}&text=${text}`, '_blank')
}

function shareWhatsapp() {
  if (!code.value) return
  const text = encodeURIComponent(
    `Xalqaro innovatsion universitetga ariza topshirishni xohlasangiz mana havola: ${code.value.share_url}`,
  )
  window.open(`https://wa.me/?text=${text}`, '_blank')
}

// === Aggregates ===
const stats = computed(() => {
  const out = {
    total: refs.value.length,
    pending: 0,
    active: 0,
    spent: 0,
    paid: 0,
    cancelled: 0,
    activeAmount: 0,
  }
  for (const r of refs.value) {
    switch (r.status) {
      case 'pending':
        out.pending++
        break
      case 'active':
        out.active++
        out.activeAmount += Number(r.reward_amount) || 0
        break
      case 'spent_on_contract':
        out.spent++
        break
      case 'paid_cash':
        out.paid++
        break
      case 'cancelled':
        out.cancelled++
        break
    }
  }
  return out
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
  pending: 'Kutilmoqda (25% to\'lov)',
  active: 'Faol — ishlatish mumkin',
  spent_on_contract: 'Shartnomada ishlatildi',
  paid_cash: 'Naqd olib ketilgan',
  cancelled: 'Bekor qilingan',
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
</script>

<template>
  <div class="space-y-5">
    <PageHeader
      title="Referal dasturi"
      subtitle="Do'stingizni taklif qiling — har biri uchun 500,000 so'm bonus."
      :crumbs="[{ label: 'Bosh sahifa', to: '/applicant' }, { label: 'Referal' }]"
    />

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else-if="code">
      <!-- Hero: link + share -->
      <section class="card overflow-hidden">
        <div class="p-5 sm:p-6 bg-gradient-to-br from-emerald-50 via-emerald-50/50 to-transparent dark:from-emerald-500/10 dark:via-emerald-500/5">
          <div class="flex items-start gap-3 mb-3">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-emerald-600 text-white shadow-md">
              <Gift class="w-5 h-5" />
            </span>
            <div>
              <h2 class="font-semibold text-slate-900 dark:text-slate-100">Sizning referal havolangiz</h2>
              <p class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                Bu havolani ulashing. Havola orqali ro'yxatdan o'tgan abituriyent shartnomasining 25% to'lovi tasdiqlangach, sizga
                <strong>500,000 so'm</strong> bonus yoziladi.
              </p>
            </div>
          </div>

          <div class="flex items-stretch gap-2 mb-3">
            <input :value="code.share_url" readonly
                   class="input flex-1 font-mono text-xs bg-white dark:bg-slate-900 truncate" />
            <button class="inline-flex items-center justify-center gap-1.5 px-4 rounded-lg text-sm font-semibold bg-brand-600 hover:bg-brand-700 text-white shrink-0"
                    @click="copyLink">
              <Check v-if="copied" class="w-4 h-4" />
              <Copy v-else class="w-4 h-4" />
              <span class="hidden sm:inline">{{ copied ? 'Nusxalandi' : 'Nusxalash' }}</span>
            </button>
          </div>

          <div class="flex flex-wrap gap-2">
            <button class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-900 text-sky-700 dark:text-sky-300 ring-1 ring-sky-200 dark:ring-sky-700/40 hover:bg-sky-50 dark:hover:bg-sky-500/10"
                    @click="shareTelegram">
              <Send class="w-3.5 h-3.5" /> Telegram
            </button>
            <button class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-200 dark:ring-emerald-700/40 hover:bg-emerald-50 dark:hover:bg-emerald-500/10"
                    @click="shareWhatsapp">
              <Phone class="w-3.5 h-3.5" /> WhatsApp
            </button>
            <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 ring-1 ring-slate-200/70 dark:ring-slate-700/40">
              <Share2 class="w-3.5 h-3.5" />
              Kod: <strong class="ml-1">{{ code.referral_code }}</strong>
            </span>
          </div>
        </div>
      </section>

      <!-- KPI tiles -->
      <section class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="card p-4">
          <div class="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400">
            <Users class="w-3 h-3" /> Taklif qilgan
          </div>
          <div class="mt-1 text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{{ stats.total }}</div>
        </div>
        <div class="card p-4">
          <div class="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-amber-700 dark:text-amber-300">
            <Clock class="w-3 h-3" /> Kutilmoqda
          </div>
          <div class="mt-1 text-2xl font-bold tabular-nums text-amber-700 dark:text-amber-300">{{ stats.pending }}</div>
        </div>
        <div class="card p-4">
          <div class="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 class="w-3 h-3" /> Faol bonus
          </div>
          <div class="mt-1 text-2xl font-bold tabular-nums text-emerald-700 dark:text-emerald-300">{{ stats.active }}</div>
        </div>
        <div class="card p-4">
          <div class="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-brand-700 dark:text-brand-300">
            <Wallet class="w-3 h-3" /> Faol summa
          </div>
          <div class="mt-1 text-xl font-bold tabular-nums text-brand-700 dark:text-brand-300">{{ fmtMoney(stats.activeAmount) }}<span class="text-xs font-normal ml-1">so'm</span></div>
        </div>
      </section>

      <!-- Status help -->
      <div class="card p-4 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
        <div class="font-semibold text-slate-900 dark:text-slate-100 mb-1.5 inline-flex items-center gap-1.5">
          <AlertTriangle class="w-3.5 h-3.5 text-amber-500" /> Qoidalar
        </div>
        <ul class="list-disc pl-5 space-y-1">
          <li>Sizning kodingiz orqali yoki royhatdan otishda kodingizni belgilab abituriyent profilini tuzgan — bonus <strong>kutilmoqda</strong>.</li>
          <li>Shu abituriyent shartnomaga imzo qo'yib, <strong>25% to'lovni amalga oshirgach</strong>, bonus avtomatik <strong>faol</strong> bo'ladi.</li>
          <li>Faol bonusni o'z shartnomangizdan chegirma sifatida ishlatishingiz yoki naqd pul olib ketishingiz mumkin (keyingi fazada qo'shiladi).</li>
        </ul>
      </div>

      <!-- Referrals list -->
      <section class="card overflow-hidden">
        <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
            <Users class="w-4 h-4 text-slate-500" /> Taklif qilganlarim
          </h2>
          <span class="text-xs text-slate-500">{{ refs.length }} ta</span>
        </div>

        <div v-if="!refs.length" class="p-10">
          <EmptyState :icon="Users" title="Hali hech kim taklif qilinmagan"
                      subtitle="Yuqoridagi linkni do'stlaringizga ulashing." />
        </div>

        <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800/60">
          <li v-for="r in refs" :key="r.id" class="p-4 flex items-center gap-3">
            <span class="grid place-items-center w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-sm font-bold shrink-0">
              {{ (r.referred_full_name || '?').split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?' }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-slate-900 dark:text-slate-100 truncate">{{ r.referred_full_name || '—' }}</div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Yaratilgan: {{ fmtDate(r.created_at) }}<span v-if="r.activated_at"> · Faol: {{ fmtDate(r.activated_at) }}</span>
              </div>
            </div>
            <div class="text-right shrink-0">
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1"
                    :class="statusTone(r.status)">
                {{ STATUS_LABEL[r.status] }}
              </span>
              <div class="mt-1 text-xs tabular-nums font-bold text-slate-900 dark:text-slate-100">
                {{ fmtMoney(r.reward_amount) }} <span class="font-normal text-slate-500">so'm</span>
              </div>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
