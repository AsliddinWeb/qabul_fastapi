<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { staffApi } from '@/api/staff.api'
import StatCard from '@/components/ui/StatCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const stats = ref({
  applicants: 0,
  appsPending: 0,
  appsReview: 0,
  appsAccepted: 0,
  appsRejected: 0,
})
const loading = ref(true)

async function appCount(s?: string) {
  const r = await staffApi.applications.list({ status: s as any, page: 1, size: 1 })
  return r.total
}

onMounted(async () => {
  try {
    const [a, ap, ar, aa, arej] = await Promise.all([
      staffApi.applicants.list({ page: 1, size: 1 }).then((r) => r.total),
      appCount('topshirildi'), appCount('korib_chiqilmoqda'),
      appCount('qabul_qilindi'), appCount('rad_etildi'),
    ])
    stats.value = {
      applicants: a,
      appsPending: ap, appsReview: ar, appsAccepted: aa, appsRejected: arej,
    }
  } finally {
    loading.value = false
  }
})

const conversionRate = () => {
  const denom = stats.value.appsReview + stats.value.appsAccepted + stats.value.appsRejected
  if (!denom) return 0
  return Math.round((stats.value.appsAccepted / denom) * 100)
}
</script>

<template>
  <div class="space-y-8">
    <div>
      <h1 class="text-2xl font-bold">Direktor paneli</h1>
      <p class="mt-1 text-slate-600">Joriy qabul kampaniyasining umumiy ko'rsatkichlari.</p>
    </div>

    <Skeleton v-if="loading" type="dashboard" />

    <template v-else>
      <section>
        <h2 class="font-semibold mb-3">Abituriyentlar</h2>
        <div class="grid gap-4 sm:grid-cols-3">
          <StatCard label="Jami abituriyentlar" :value="stats.applicants" tone="brand" />
        </div>
      </section>

      <section>
        <h2 class="font-semibold mb-3">Arizalar</h2>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard label="Topshirildi" :value="stats.appsPending" tone="amber" />
          <StatCard label="Ko'rib chiqilmoqda" :value="stats.appsReview" tone="brand" />
          <StatCard label="Qabul qilindi" :value="stats.appsAccepted" tone="emerald" />
          <StatCard label="Rad etildi" :value="stats.appsRejected" tone="rose" />
          <StatCard label="Konversiya" :value="conversionRate() + '%'" tone="emerald"
                    hint="qabul qilindi / ko'rilgan" />
        </div>
      </section>
    </template>
  </div>
</template>
