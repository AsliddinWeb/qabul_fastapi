<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Plus, FileText, CheckCircle2, Trash2 } from 'lucide-vue-next'
import { contractsApi, type ContractTemplateRead } from '@/api/contracts.api'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const items = ref<ContractTemplateRead[]>([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    items.value = await contractsApi.templates()
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function activate(id: string) {
  await contractsApi.activateTemplate(id)
  await load()
}

async function remove(id: string, name: string) {
  if (!window.confirm(`O'chirilsinmi: ${name}?`)) return
  await contractsApi.deleteTemplate(id)
  await load()
}

const charCount = (t: ContractTemplateRead) =>
  (t.body_two_party?.length || 0) + (t.body_three_party?.length || 0)
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Shartnoma shabloni"
      subtitle="Bitta shablon ichida 2-tomonlama va 3-tomonlama matnlar saqlanadi. Faqat bitta shablon faol bo'la oladi."
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Sozlamalar' }]"
    >
      <RouterLink to="/admin/contract-templates/new" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi shablon
      </RouterLink>
    </PageHeader>

    <Skeleton v-if="loading" type="list" />
    <EmptyState v-else-if="!items.length" :icon="FileText" title="Shablonlar yo'q">
      <RouterLink to="/admin/contract-templates/new" class="btn-primary mt-4 inline-block">
        Birinchi shablonni yaratish
      </RouterLink>
    </EmptyState>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="t in items"
        :key="t.id"
        class="card p-5 transition-colors"
        :class="t.is_active ? 'border-brand-300 dark:border-brand-700' : ''"
      >
        <div class="flex items-center justify-between">
          <span class="font-semibold text-slate-900 dark:text-slate-100 truncate">
            {{ t.name }}
          </span>
          <span class="text-xs text-slate-400 dark:text-slate-500 shrink-0">v{{ t.version }}</span>
        </div>
        <div class="mt-2 flex flex-wrap gap-1.5">
          <span v-if="t.body_two_party"
                class="badge bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            2-tomonlama
          </span>
          <span v-if="t.body_three_party"
                class="badge bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            3-tomonlama
          </span>
          <span v-if="t.is_active"
                class="badge bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Faol
          </span>
        </div>
        <div class="mt-3 text-xs text-slate-500 dark:text-slate-400">
          {{ charCount(t) }} belgi · {{ new Date(t.created_at).toLocaleDateString('uz-UZ') }}
        </div>
        <div class="mt-4 flex gap-2">
          <RouterLink :to="`/admin/contract-templates/${t.id}`" class="btn-ghost text-sm flex-1 justify-center">
            Tahrirlash
          </RouterLink>
          <button v-if="!t.is_active" class="btn-ghost text-sm" title="Faol qilish" @click="activate(t.id)">
            <CheckCircle2 class="w-4 h-4 text-green-600" />
          </button>
          <button class="btn-ghost text-sm" title="O'chirish" @click="remove(t.id, t.name)">
            <Trash2 class="w-4 h-4 text-red-600" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
