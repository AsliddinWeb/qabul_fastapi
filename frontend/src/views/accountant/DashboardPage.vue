<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { FileText } from 'lucide-vue-next'
import { staffApi } from '@/api/staff.api'
import StatCard from '@/components/ui/StatCard.vue'

const stats = ref({ accepted: 0 })
const loading = ref(true)

onMounted(async () => {
  try {
    const r = await staffApi.applications.list({ status: 'qabul_qilindi', page: 1, size: 1 })
    stats.value = { accepted: r.total }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Buxgalter paneli</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">Shartnomalar va to'lovlar boshqaruvi.</p>
    </div>

    <div v-if="!loading" class="grid gap-4 sm:grid-cols-2">
      <StatCard label="Qabul qilingan arizalar" :value="stats.accepted" tone="emerald" />
    </div>

    <section class="card p-6">
      <h2 class="font-semibold mb-3 text-slate-900 dark:text-slate-100">To'lovlarni boshqarish</h2>
      <p class="text-sm text-slate-600 dark:text-slate-400 mb-3">
        Shartnoma raqami orqali to'lovlarni qo'shing va tasdiqlang.
      </p>
      <RouterLink to="/accountant/contracts" class="btn-primary">
        <FileText class="w-4 h-4" /> Shartnomalarga o'tish
      </RouterLink>
    </section>
  </div>
</template>
