<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Check, Clock, GraduationCap, FileSignature, ClipboardList, ArrowRight,
  User as UserIcon, IdCard, Award,
} from 'lucide-vue-next'
import { applicantsApi, type ApplicantDetailed } from '@/api/applicants.api'
import { applicationsApi, type ApplicationDetailed } from '@/api/applications.api'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import { useAuthStore } from '@/stores/auth'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { APPLICATION_STATUS, CONTRACT_STATUS, tr } from '@/utils/labels'

const auth = useAuthStore()

const profile = ref<ApplicantDetailed | null>(null)
const applications = ref<ApplicationDetailed[]>([])
const contracts = ref<ContractDetailed[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [p, apps, cons] = await Promise.all([
      applicantsApi.me().catch(() => null),
      applicationsApi.myList().catch(() => []),
      contractsApi.myList().catch(() => []),
    ])
    profile.value = p
    applications.value = apps
    contracts.value = cons
  } finally { loading.value = false }
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h >= 5 && h < 12)  return 'Xayrli tong'
  if (h >= 12 && h < 17) return 'Xayrli kun'
  if (h >= 17 && h < 22) return 'Xayrli kech'
  return 'Hayrli oqshom'
})

const firstName = computed(() => {
  const f = profile.value?.first_name?.trim()
  if (f) return f
  const fn = auth.user?.full_name?.trim()
  if (fn) return fn.split(/\s+/)[0]
  return ''
})

const steps = computed(() => [
  {
    key: 'profile',
    title: "Shaxsiy ma'lumotlar",
    icon: UserIcon,
    to: '/applicant/profile',
    done: !!(profile.value?.last_name && profile.value?.first_name && profile.value?.birth_date),
  },
  {
    key: 'passport',
    title: "Pasport va PINFL",
    icon: IdCard,
    to: '/applicant/profile',
    done: !!(profile.value?.passport_series && profile.value?.pinfl),
  },
  {
    key: 'diplom',
    title: "Diplom yoki attestat",
    icon: Award,
    to: '/applicant/profile',
    done: !!(profile.value?.diplom || profile.value?.transfer_diplom),
  },
  {
    key: 'apply',
    title: "Yo'nalishga ariza",
    icon: ClipboardList,
    to: '/applicant/programs',
    done: applications.value.length > 0,
  },
])

const completedSteps = computed(() => steps.value.filter(s => s.done).length)
const progressPercent = computed(() =>
  Math.round((completedSteps.value / steps.value.length) * 100),
)

const activeApplication = computed(() => {
  // Prefer the most recent open one
  const order = ['topshirildi', 'korib_chiqilmoqda', 'qabul_qilindi', 'rad_etildi']
  const sorted = [...applications.value].sort(
    (a, b) => order.indexOf(b.status) - order.indexOf(a.status)
            || new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
  return sorted[0] || null
})

const activeContract = computed(() =>
  contracts.value.find((c) => c.status !== 'cancelled') || null,
)

function fmtMoney(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!n || isNaN(n)) return '—'
  return Number(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      :title="firstName ? `${greeting}, ${firstName}!` : greeting"
      subtitle="Qabul jarayoningiz holati"
      :crumbs="[]"
    />

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else>
      <!-- Setup progress hero -->
      <section v-if="progressPercent < 100"
               class="rounded-2xl p-6 sm:p-8 text-white relative overflow-hidden"
               style="background: linear-gradient(135deg, rgb(79 70 229) 0%, rgb(139 92 246) 100%);">
        <div class="absolute inset-0 opacity-25"
             style="background-image: radial-gradient(circle at 80% 20%, rgba(255,255,255,0.3), transparent 50%);"></div>
        <div class="relative grid sm:grid-cols-3 gap-6 items-center">
          <div class="sm:col-span-2">
            <div class="text-xs uppercase tracking-wider opacity-80 mb-1">Qabul jarayoni</div>
            <h2 class="text-2xl sm:text-3xl font-bold mb-2">
              {{ completedSteps }} / {{ steps.length }} qadam bajarildi
            </h2>
            <p class="opacity-90 text-sm sm:text-base">
              Quyidagi qadamlarni to'ldirib, arizangizni topshirishga tayyorgarlik ko'ring.
            </p>
          </div>
          <div class="text-center sm:text-right">
            <div class="text-5xl sm:text-6xl font-bold tabular-nums">{{ progressPercent }}%</div>
          </div>
        </div>
        <div class="relative mt-5 h-2 rounded-full bg-white/20 overflow-hidden">
          <div class="h-full rounded-full bg-white transition-all"
               :style="{ width: progressPercent + '%' }"></div>
        </div>
      </section>

      <section v-else class="rounded-2xl p-6 sm:p-8 text-white relative overflow-hidden"
               style="background: linear-gradient(135deg, rgb(5 150 105) 0%, rgb(20 184 166) 100%);">
        <div class="absolute inset-0 opacity-25"
             style="background-image: radial-gradient(circle at 80% 20%, rgba(255,255,255,0.3), transparent 50%);"></div>
        <div class="relative flex items-center gap-4">
          <span class="grid place-items-center w-14 h-14 rounded-2xl bg-white/20 backdrop-blur shrink-0">
            <Check class="w-7 h-7" />
          </span>
          <div>
            <h2 class="text-2xl sm:text-3xl font-bold">Hammasi tayyor!</h2>
            <p class="opacity-90 mt-1">Ma'lumotlar to'liq, arizangiz topshirilgan. Status uchun "Arizalarim" bo'limini ko'ring.</p>
          </div>
        </div>
      </section>

      <!-- Steps -->
      <section class="card p-6">
        <h2 class="font-bold text-lg mb-4 text-slate-900 dark:text-slate-100">Qadamlar</h2>
        <ol class="space-y-2">
          <RouterLink
            v-for="(s, i) in steps" :key="s.key" :to="s.to"
            class="flex items-center gap-4 p-3 -mx-3 rounded-xl transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40 group"
          >
            <span class="grid place-items-center w-10 h-10 rounded-xl shrink-0 transition-transform group-hover:scale-105"
                  :class="s.done
                    ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300'
                    : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'">
              <Check v-if="s.done" class="w-5 h-5" />
              <component v-else :is="s.icon" class="w-5 h-5" />
            </span>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-slate-900 dark:text-slate-100">{{ s.title }}</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                <template v-if="s.done">Bajarildi</template>
                <template v-else>{{ i + 1 }}-qadam</template>
              </div>
            </div>
            <ArrowRight class="w-4 h-4 text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-200 transition-colors" />
          </RouterLink>
        </ol>
      </section>

      <!-- Two-column: latest application + active contract -->
      <section class="grid sm:grid-cols-2 gap-4">
        <!-- Application -->
        <RouterLink v-if="activeApplication"
                    :to="`/applicant/applications/${activeApplication.id}`"
                    class="card-hover p-6 group">
          <div class="flex items-center gap-3 mb-4">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
              <ClipboardList class="w-5 h-5" />
            </span>
            <div>
              <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Joriy ariza</div>
              <div class="font-mono text-xs text-slate-700 dark:text-slate-300">{{ activeApplication.application_number }}</div>
            </div>
          </div>
          <h3 class="font-bold text-base text-slate-900 dark:text-slate-100 mb-2 line-clamp-2 min-h-[3rem]">
            {{ activeApplication.program_name || "Yo'nalish" }}
          </h3>
          <div class="flex items-center justify-between mt-2">
            <StatusBadge :status="activeApplication.status" :label="tr(APPLICATION_STATUS, activeApplication.status)" />
            <span class="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 dark:text-brand-300 group-hover:gap-2 transition-all">
              Tafsilot
              <ArrowRight class="w-3 h-3" />
            </span>
          </div>
        </RouterLink>
        <RouterLink v-else to="/applicant/programs"
                    class="card-hover p-6 group flex flex-col items-center justify-center text-center">
          <span class="grid place-items-center w-12 h-12 rounded-xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500 mb-3">
            <ClipboardList class="w-5 h-5" />
          </span>
          <div class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Hali ariza yo'q</div>
          <div class="text-xs text-slate-500 dark:text-slate-400">Yo'nalish tanlash uchun bosing</div>
        </RouterLink>

        <!-- Contract -->
        <RouterLink v-if="activeContract"
                    :to="`/applicant/contracts/${activeContract.id}`"
                    class="card-hover p-6 group">
          <div class="flex items-center gap-3 mb-4">
            <span class="grid place-items-center w-10 h-10 rounded-xl bg-teal-100 text-teal-600 dark:bg-teal-500/20 dark:text-teal-300">
              <FileSignature class="w-5 h-5" />
            </span>
            <div>
              <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Shartnoma</div>
              <div class="font-mono text-xs text-slate-700 dark:text-slate-300">{{ activeContract.contract_number }}</div>
            </div>
          </div>
          <div class="text-base font-bold text-slate-900 dark:text-slate-100 tabular-nums mb-1">
            {{ fmtMoney(activeContract.total_amount) }}
            <span class="text-xs font-normal text-slate-500">{{ activeContract.currency }}</span>
          </div>
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-3">
            To'langan: <strong class="text-emerald-600 dark:text-emerald-400">{{ fmtMoney(activeContract.paid_amount) }}</strong>
          </div>
          <div class="flex items-center justify-between mt-2">
            <StatusBadge :status="activeContract.status" :label="tr(CONTRACT_STATUS, activeContract.status)" />
            <span class="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 dark:text-brand-300 group-hover:gap-2 transition-all">
              PDF <ArrowRight class="w-3 h-3" />
            </span>
          </div>
        </RouterLink>
        <div v-else class="card p-6 flex flex-col items-center justify-center text-center">
          <span class="grid place-items-center w-12 h-12 rounded-xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500 mb-3">
            <FileSignature class="w-5 h-5" />
          </span>
          <div class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Shartnoma kutilmoqda</div>
          <div class="text-xs text-slate-500 dark:text-slate-400">
            Ariza qabul qilingach paydo bo'ladi
          </div>
        </div>
      </section>

      <!-- Quick links -->
      <section class="grid sm:grid-cols-3 gap-3">
        <RouterLink to="/applicant/programs"
                    class="card-hover p-4 flex items-center gap-3 group">
          <span class="grid place-items-center w-10 h-10 rounded-xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300">
            <GraduationCap class="w-5 h-5" />
          </span>
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-sm text-slate-900 dark:text-slate-100">Yo'nalishlar</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">Tanlash</div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-400 group-hover:text-slate-700 transition-colors" />
        </RouterLink>
        <RouterLink to="/applicant/applications"
                    class="card-hover p-4 flex items-center gap-3 group">
          <span class="grid place-items-center w-10 h-10 rounded-xl bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
            <ClipboardList class="w-5 h-5" />
          </span>
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-sm text-slate-900 dark:text-slate-100">Arizalarim</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">{{ applications.length }} ta</div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-400 group-hover:text-slate-700 transition-colors" />
        </RouterLink>
        <RouterLink to="/applicant/contracts"
                    class="card-hover p-4 flex items-center gap-3 group">
          <span class="grid place-items-center w-10 h-10 rounded-xl bg-teal-100 text-teal-600 dark:bg-teal-500/20 dark:text-teal-300">
            <FileSignature class="w-5 h-5" />
          </span>
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-sm text-slate-900 dark:text-slate-100">Shartnomalarim</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">{{ contracts.length }} ta</div>
          </div>
          <ArrowRight class="w-4 h-4 text-slate-400 group-hover:text-slate-700 transition-colors" />
        </RouterLink>
      </section>
    </template>
  </div>
</template>
