<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { FileText } from 'lucide-vue-next'
import { staffApi } from '@/api/staff.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { APPLICATION_STATUS, tr } from '@/utils/labels'
import Skeleton from '@/components/ui/Skeleton.vue'

const items = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const accepted = await staffApi.applications.list({ status: 'qabul_qilindi', page: 1, size: 100 })
    items.value = accepted.items
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Shartnomalar bo'yicha to'lovlar</h1>
      <p class="text-sm text-slate-600 dark:text-slate-400">
        Shartnomalashtirilgan abituriyentlar ro'yxati. To'lovlarni boshqarish uchun ariza raqamiga bosing.
      </p>
    </div>

    <Skeleton v-if="loading" type="list" />
    <EmptyState v-else-if="!items.length" :icon="FileText" title="Shartnomalashtirilgan arizalar yo'q" />

    <div v-else class="card overflow-hidden">
      <table class="data-table">
        <thead>
          <tr>
            <th>Ariza №</th>
            <th>Yo'nalish</th>
            <th>Holati</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in items" :key="a.id">
            <td class="font-mono text-xs text-slate-600 dark:text-slate-300">{{ a.application_number }}</td>
            <td class="text-slate-900 dark:text-slate-100">{{ a.program_name || a.program_name_uz || '—' }}</td>
            <td><StatusBadge :status="a.status" :label="tr(APPLICATION_STATUS, a.status)" /></td>
            <td class="text-right">
              <RouterLink :to="`/accountant/applications/${a.id}/payments`"
                          class="text-brand-600 dark:text-brand-300 hover:underline text-sm">
                To'lovlar
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
