<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Send, Eye, CheckCircle2, XCircle, Clock,
  GraduationCap, FileSignature, AlertTriangle, Building2, BookOpen,
} from 'lucide-vue-next'
import { applicationsApi, type ApplicationDetailed } from '@/api/applications.api'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { APPLICATION_STATUS, ADMISSION_TYPE, tr } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const application = ref<ApplicationDetailed | null>(null)
const contract = ref<ContractDetailed | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const list = await applicationsApi.myList()
    application.value = list.find((a) => a.id === id.value) || null
    if (application.value) {
      const contracts = await contractsApi.myList().catch(() => [])
      contract.value = contracts.find((c) => c.application_id === id.value && c.status !== 'cancelled') || null
    }
  } finally { loading.value = false }
})

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

interface TimelineStep {
  key: string
  label: string
  icon: any
  done: boolean
  active?: boolean
  date?: string | null
  failed?: boolean
}

const timeline = computed<TimelineStep[]>(() => {
  const a = application.value
  if (!a) return []
  const status = a.status

  const submitted: TimelineStep = {
    key: 'topshirildi',
    label: 'Ariza topshirildi',
    icon: Send,
    done: true,
    date: a.submitted_at || a.created_at,
  }
  const review: TimelineStep = {
    key: 'korib_chiqilmoqda',
    label: "Ko'rib chiqilmoqda",
    icon: Eye,
    done: status === 'korib_chiqilmoqda' || status === 'qabul_qilindi' || status === 'rad_etildi',
    active: status === 'korib_chiqilmoqda',
  }
  const decision: TimelineStep = {
    key: 'decision',
    label: status === 'rad_etildi' ? 'Rad etildi' : 'Qabul qilindi',
    icon: status === 'rad_etildi' ? XCircle : CheckCircle2,
    done: status === 'qabul_qilindi' || status === 'rad_etildi',
    active: status === 'qabul_qilindi' || status === 'rad_etildi',
    failed: status === 'rad_etildi',
  }
  return [submitted, review, decision]
})
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="!application">
    <PageHeader
      title="Ariza topilmadi"
      :crumbs="[{ label: 'Bosh sahifa', to: '/applicant' }, { label: 'Arizalarim', to: '/applicant/applications' }]"
    >
      <button class="btn-ghost" @click="router.push('/applicant/applications')">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>
    <div class="card p-12 text-center text-slate-500">
      Bu ariza ro'yxatda yo'q yoki sizniki emas.
    </div>
  </div>

  <div v-else class="space-y-6">
    <PageHeader
      :title="application.program_name || `Ariza ${application.application_number}`"
      :subtitle="`${tr(ADMISSION_TYPE, application.admission_type)} · ${application.application_number}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/applicant' }, { label: 'Arizalarim', to: '/applicant/applications' }]"
    >
      <StatusBadge :status="application.status" :label="tr(APPLICATION_STATUS, application.status)" />
    </PageHeader>

    <!-- Status timeline -->
    <section class="card p-6 sm:p-7">
      <h2 class="font-bold text-lg mb-6 text-slate-900 dark:text-slate-100">Ariza jarayoni</h2>
      <ol class="relative">
        <li v-for="(step, idx) in timeline" :key="step.key"
            class="flex items-start gap-4 pb-6 last:pb-0 relative">
          <span v-if="idx < timeline.length - 1"
                class="absolute left-[19px] top-[42px] bottom-0 w-px"
                :class="step.done ? 'bg-emerald-400 dark:bg-emerald-600' : 'bg-slate-200 dark:bg-slate-700'"></span>

          <span class="grid place-items-center w-10 h-10 rounded-xl shrink-0 ring-4 ring-[rgb(var(--card,255_255_255))]"
                :class="step.failed
                  ? 'bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-300'
                  : step.done
                    ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300'
                    : step.active
                      ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300'
                      : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'">
            <component :is="step.icon" class="w-5 h-5" />
          </span>

          <div class="flex-1 min-w-0 pt-1.5">
            <div class="font-bold text-base text-slate-900 dark:text-slate-100">{{ step.label }}</div>
            <div v-if="step.date" class="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {{ fmtDate(step.date) }}
            </div>
            <div v-else-if="step.active" class="text-xs text-amber-600 dark:text-amber-400 mt-1 inline-flex items-center gap-1">
              <Clock class="w-3 h-3" /> Joriy bosqich
            </div>
            <div v-else class="text-xs text-slate-400 mt-1">Kutilmoqda</div>
          </div>
        </li>
      </ol>

      <!-- Rejection reason callout -->
      <div v-if="application.status === 'rad_etildi' && application.rejection_reason"
           class="mt-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200/60 dark:border-rose-700/30 flex items-start gap-3">
        <AlertTriangle class="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
        <div>
          <div class="font-semibold text-sm text-rose-900 dark:text-rose-200">Rad etish sababi</div>
          <p class="text-sm text-rose-800 dark:text-rose-300 mt-1">{{ application.rejection_reason }}</p>
        </div>
      </div>
    </section>

    <!-- Application details -->
    <section class="card p-6 sm:p-7">
      <h2 class="font-bold text-lg mb-5 text-slate-900 dark:text-slate-100">Ariza ma'lumotlari</h2>
      <dl class="grid sm:grid-cols-2 gap-x-8 gap-y-4">
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Yo'nalish</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
            <GraduationCap class="w-4 h-4 text-slate-400" />
            {{ application.program_name || '—' }}
          </dd>
        </div>
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Filial</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
            <Building2 class="w-4 h-4 text-slate-400" />
            {{ application.branch_name || '—' }}
          </dd>
        </div>
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Qabul turi</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100">
            {{ tr(ADMISSION_TYPE, application.admission_type) }}
          </dd>
        </div>
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Ariza raqami</dt>
          <dd class="text-sm font-mono font-medium text-slate-900 dark:text-slate-100">
            {{ application.application_number }}
          </dd>
        </div>
        <div>
          <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Topshirilgan vaqt</dt>
          <dd class="text-sm font-medium text-slate-900 dark:text-slate-100">
            {{ fmtDate(application.submitted_at || application.created_at) }}
          </dd>
        </div>
      </dl>
    </section>

    <!-- Contract link -->
    <section v-if="contract" class="card p-6 sm:p-7">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-start gap-4 min-w-0">
          <span class="grid place-items-center w-12 h-12 rounded-xl bg-teal-100 text-teal-600 dark:bg-teal-500/20 dark:text-teal-300 shrink-0">
            <FileSignature class="w-5 h-5" />
          </span>
          <div class="min-w-0">
            <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Shartnoma</div>
            <div class="font-bold text-base text-slate-900 dark:text-slate-100 truncate">
              {{ contract.contract_number }}
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {{ Number(contract.total_amount).toLocaleString('uz-UZ') }} {{ contract.currency }} ·
              <span class="capitalize">{{ contract.status }}</span>
            </div>
          </div>
        </div>
        <RouterLink :to="`/applicant/contracts/${contract.id}`" class="btn-secondary btn-sm shrink-0">
          Ko'rish
        </RouterLink>
      </div>
    </section>

    <section v-else-if="application.status === 'qabul_qilindi'" class="card p-6 bg-amber-50/50 dark:bg-amber-500/5 border-amber-200 dark:border-amber-700/40">
      <div class="flex items-start gap-3">
        <BookOpen class="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div>
          <div class="font-semibold text-amber-900 dark:text-amber-200">Shartnoma kutilmoqda</div>
          <p class="text-sm text-amber-800 dark:text-amber-300 mt-1">
            Operator siz uchun shartnoma rasmiylashtiradi. Tayyor bo'lgach bu yerda paydo bo'ladi.
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
