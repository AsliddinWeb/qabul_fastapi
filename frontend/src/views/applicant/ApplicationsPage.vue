<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ClipboardList, ArrowRight, Send, Eye, CheckCircle2, XCircle, Clock,
} from 'lucide-vue-next'
import { applicationsApi, type ApplicationDetailed } from '@/api/applications.api'
import { APPLICATION_STATUS, ADMISSION_TYPE, tr } from '@/utils/labels'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const items = ref<ApplicationDetailed[]>([])
const loading = ref(true)

onMounted(async () => {
  try { items.value = await applicationsApi.myList() }
  catch { items.value = [] }
  finally { loading.value = false }
})

const STATUS_TONE: Record<string, string> = {
  topshirildi:       'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  korib_chiqilmoqda: 'bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300',
  qabul_qilindi:     'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
  rad_etildi:        'bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
}
const STATUS_ICON: Record<string, any> = {
  topshirildi:       Send,
  korib_chiqilmoqda: Eye,
  qabul_qilindi:     CheckCircle2,
  rad_etildi:        XCircle,
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const stats = computed(() => ({
  total: items.value.length,
  inReview: items.value.filter(a => a.status === 'topshirildi' || a.status === 'korib_chiqilmoqda').length,
  accepted: items.value.filter(a => a.status === 'qabul_qilindi').length,
  rejected: items.value.filter(a => a.status === 'rad_etildi').length,
}))
</script>

<template>
  <div>
    <PageHeader
      title="Mening arizalarim"
      :subtitle="loading ? 'Yuklanmoqda...' : `${items.length} ta ariza`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/applicant' }]"
    >
      <RouterLink to="/applicant/programs" class="btn-primary">
        <ClipboardList class="w-4 h-4" /> Yangi ariza
      </RouterLink>
    </PageHeader>

    <Skeleton v-if="loading" type="list" />

    <div v-else-if="!items.length" class="card p-12">
      <EmptyState
        :icon="ClipboardList"
        title="Hali ariza topshirmagansiz"
        subtitle="Yo'nalishlar ro'yxatidan o'zingizga mosini tanlab ariza qoldiring"
      >
        <RouterLink to="/applicant/programs" class="btn-primary mt-4 inline-flex">
          Yo'nalishlarni ko'rish
        </RouterLink>
      </EmptyState>
    </div>

    <template v-else>
      <!-- Quick stats -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div class="card p-4">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Jami</div>
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-100">{{ stats.total }}</div>
        </div>
        <div class="card p-4">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Ko'rilmoqda</div>
          <div class="text-2xl font-bold text-amber-600 dark:text-amber-400">{{ stats.inReview }}</div>
        </div>
        <div class="card p-4">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Qabul qilindi</div>
          <div class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{{ stats.accepted }}</div>
        </div>
        <div class="card p-4">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Rad etildi</div>
          <div class="text-2xl font-bold text-rose-600 dark:text-rose-400">{{ stats.rejected }}</div>
        </div>
      </div>

      <!-- Application cards -->
      <div class="space-y-3">
        <RouterLink v-for="a in items" :key="a.id"
                    :to="`/applicant/applications/${a.id}`"
                    class="card-hover p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center gap-4 group">
          <span class="grid place-items-center w-12 h-12 rounded-xl shrink-0 transition-transform group-hover:scale-105"
                :class="STATUS_TONE[a.status] || 'bg-slate-100 text-slate-600'">
            <component :is="STATUS_ICON[a.status] || Clock" class="w-5 h-5" />
          </span>

          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2 mb-1.5">
              <span class="font-mono text-xs text-slate-500 dark:text-slate-400">{{ a.application_number }}</span>
              <span class="pill bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                {{ tr(ADMISSION_TYPE, a.admission_type) }}
              </span>
            </div>
            <h3 class="font-bold text-base text-slate-900 dark:text-slate-100 truncate">
              {{ a.program_name || "Yo'nalish ko'rsatilmagan" }}
            </h3>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
              <span v-if="a.branch_name">{{ a.branch_name }} · </span>
              {{ fmtDate(a.created_at) }}
            </div>
          </div>

          <div class="flex items-center gap-3">
            <StatusBadge :status="a.status" :label="tr(APPLICATION_STATUS, a.status)" />
            <ArrowRight class="w-4 h-4 text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-200 transition-colors" />
          </div>
        </RouterLink>
      </div>
    </template>
  </div>
</template>
