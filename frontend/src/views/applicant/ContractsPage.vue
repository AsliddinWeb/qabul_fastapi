<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { FileSignature, FileText, ArrowRight } from 'lucide-vue-next'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import { CONTRACT_STATUS, CONTRACT_TYPE, tr } from '@/utils/labels'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const items = ref<ContractDetailed[]>([])
const loading = ref(true)

onMounted(async () => {
  try { items.value = await contractsApi.myList() }
  catch { items.value = [] }
  finally { loading.value = false }
})

function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!n || isNaN(n)) return '—'
  return Number(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short', year: 'numeric' })
}

// Cancelled contracts shouldn't contribute to summary totals or remain
// clickable — they're shown as muted, read-only entries with amounts hidden.
const activeContracts = computed(() => items.value.filter(c => c.status !== 'cancelled'))

const stats = computed(() => {
  const totalAmount = activeContracts.value.reduce((s, c) => s + parseFloat(c.total_amount || '0'), 0)
  const paidAmount  = activeContracts.value.reduce((s, c) => s + parseFloat(c.paid_amount  || '0'), 0)
  return {
    count: activeContracts.value.length,
    totalAmount,
    paidAmount,
    remaining: Math.max(0, totalAmount - paidAmount),
  }
})

function paidPercent(c: ContractDetailed): number {
  const tot = parseFloat(c.total_amount || '0')
  const paid = parseFloat(c.paid_amount || '0')
  if (!tot) return 0
  return Math.min(100, Math.round((paid / tot) * 100))
}
</script>

<template>
  <div>
    <PageHeader
      title="Shartnomalarim"
      :subtitle="loading ? 'Yuklanmoqda...' : `${items.length} ta shartnoma`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/applicant' }]"
    />

    <Skeleton v-if="loading" type="list" />

    <div v-else-if="!items.length" class="card p-12">
      <EmptyState
        :icon="FileSignature"
        title="Hali shartnoma yo'q"
        subtitle="Arizangiz qabul qilingach, operator shartnomani tayyorlaydi"
      >
        <RouterLink to="/applicant/applications" class="btn-secondary mt-4 inline-flex">
          Arizalarimni ko'rish
        </RouterLink>
      </EmptyState>
    </div>

    <template v-else>
      <!-- Summary -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <div class="card p-5">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
            Jami summa
          </div>
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">
            {{ fmtMoney(stats.totalAmount) }}
            <span class="text-sm font-normal text-slate-500">so'm</span>
          </div>
        </div>
        <div class="card p-5">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
            To'langan
          </div>
          <div class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
            {{ fmtMoney(stats.paidAmount) }}
            <span class="text-sm font-normal text-slate-500">so'm</span>
          </div>
        </div>
        <div class="card p-5">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
            Qoldiq
          </div>
          <div class="text-2xl font-bold tabular-nums"
               :class="stats.remaining > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'">
            {{ fmtMoney(stats.remaining) }}
            <span class="text-sm font-normal text-slate-500">so'm</span>
          </div>
        </div>
      </div>

      <!-- Contracts -->
      <div class="space-y-3">
        <component
          v-for="c in items" :key="c.id"
          :is="c.status === 'cancelled' ? 'div' : 'router-link'"
          :to="c.status === 'cancelled' ? undefined : `/applicant/contracts/${c.id}`"
          class="card-hover p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center gap-4 group"
          :class="c.status === 'cancelled' ? 'opacity-60 cursor-not-allowed pointer-events-none' : ''"
        >
          <span class="grid place-items-center w-12 h-12 rounded-xl shrink-0 bg-teal-100 text-teal-600 dark:bg-teal-500/20 dark:text-teal-300 transition-transform group-hover:scale-105"
                :class="c.status === 'cancelled' ? 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500' : ''">
            <FileText class="w-5 h-5" />
          </span>

          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2 mb-1">
              <span class="font-mono font-bold text-sm"
                    :class="c.status === 'cancelled' ? 'text-slate-500 dark:text-slate-400 line-through' : 'text-slate-900 dark:text-slate-100'">
                {{ c.contract_number }}
              </span>
              <span class="pill bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                {{ tr(CONTRACT_TYPE, c.type) }}
              </span>
            </div>

            <!-- Active contract: show amounts + progress -->
            <template v-if="c.status !== 'cancelled'">
              <div class="text-base font-bold text-slate-900 dark:text-slate-100 tabular-nums">
                {{ fmtMoney(c.total_amount) }}
                <span class="text-xs font-normal text-slate-500">{{ c.currency }}</span>
              </div>
              <div class="mt-2.5 max-w-xs">
                <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1">
                  <span>To'lov: {{ fmtMoney(c.paid_amount) }}</span>
                  <span class="font-mono">{{ paidPercent(c) }}%</span>
                </div>
                <div class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div class="h-full rounded-full bg-emerald-500 transition-all"
                       :style="{ width: paidPercent(c) + '%' }"></div>
                </div>
              </div>
              <div v-if="c.signed_at" class="text-xs text-slate-500 dark:text-slate-400 mt-2">
                Imzolangan: {{ fmtDate(c.signed_at) }}
              </div>
            </template>

            <!-- Cancelled: hide amounts, show explanation -->
            <template v-else>
              <div class="text-base font-bold tabular-nums text-slate-400 dark:text-slate-500">—</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Bekor qilingan shartnoma
              </div>
            </template>
          </div>

          <div class="flex items-center gap-3">
            <StatusBadge :status="c.status" :label="tr(CONTRACT_STATUS, c.status)" />
            <ArrowRight v-if="c.status !== 'cancelled'"
                        class="w-4 h-4 text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-200 transition-colors" />
          </div>
        </component>
      </div>
    </template>
  </div>
</template>
