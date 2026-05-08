<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AxiosError } from 'axios'
import { Check } from 'lucide-vue-next'
import { programsApi, type ProgramRead } from '@/api/programs.api'
import { applicationsApi, type ApplicationDetailed } from '@/api/applications.api'
import Skeleton from '@/components/ui/Skeleton.vue'

const programs = ref<ProgramRead[]>([])
const myApps = ref<ApplicationDetailed[]>([])
const loading = ref(true)
const submitting = ref<string | null>(null)
const message = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

const appliedProgramIds = computed(
  () => new Set(myApps.value.map((a) => a.program_id)),
)

onMounted(async () => {
  try {
    const [progs, apps] = await Promise.all([
      programsApi.list({ active_only: true }),
      applicationsApi.myList().catch(() => []),
    ])
    programs.value = progs
    myApps.value = apps
  } finally {
    loading.value = false
  }
})

async function apply(p: ProgramRead) {
  submitting.value = p.id
  message.value = null
  try {
    await applicationsApi.submit({
      admission_type: 'yangi_qabul',
      branch_id: p.branch_id,
      education_level_id: p.education_level_id,
      education_form_id: p.education_form_id,
      program_id: p.id,
    })
    message.value = { type: 'ok', text: 'Ariza yuborildi' }
    myApps.value = await applicationsApi.myList()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    message.value = {
      type: 'err',
      text: ax.response?.data?.error?.message || "Ariza yuborib bo'lmadi",
    }
  } finally {
    submitting.value = null
  }
}
</script>

<template>
  <div class="max-w-5xl space-y-6">
    <div>
      <h1 class="text-2xl font-bold">Yo'nalishlar</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">Joriy o'quv yili uchun mavjud yo'nalishlar.</p>
    </div>

    <div v-if="message" class="text-sm rounded-lg p-3"
         :class="message.type === 'ok'
           ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300'
           : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'">
      {{ message.text }}
    </div>

    <Skeleton v-if="loading" type="list" />
    <div v-else-if="!programs.length" class="text-slate-500 dark:text-slate-400">
      Hozircha yo'nalishlar mavjud emas.
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="p in programs"
        :key="p.id"
        class="card p-5 flex flex-col"
      >
        <div class="text-xs text-slate-500 dark:text-slate-400 font-mono">{{ p.code }}</div>
        <div class="mt-1 font-semibold text-slate-900 dark:text-slate-100">{{ p.name }}</div>
        <div class="text-sm text-slate-500 dark:text-slate-400">{{ p.branch_name || '' }}</div>

        <div class="mt-3 flex flex-wrap gap-2 text-xs">
          <span v-if="p.education_level_name" class="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded">
            {{ p.education_level_name }}
          </span>
          <span v-if="p.education_form_name" class="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded">
            {{ p.education_form_name }}
          </span>
        </div>

        <div class="mt-4 text-sm">
          <div class="text-slate-500 dark:text-slate-400">Yillik to'lov</div>
          <div class="font-semibold text-slate-900 dark:text-slate-100">
            {{ Number(p.tuition_fee).toLocaleString('uz-UZ').replace(/,/g, ' ') }} so'm
          </div>
          <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ (p as any).study_duration_years }} yil</div>
        </div>

        <div class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button
            v-if="appliedProgramIds.has(p.id)"
            class="btn-ghost w-full justify-center"
            disabled
          >
            <Check class="w-4 h-4" /> Ariza topshirilgan
          </button>
          <button
            v-else
            class="btn-primary w-full justify-center"
            :disabled="submitting === p.id"
            @click="apply(p)"
          >
            {{ submitting === p.id ? 'Yuborilmoqda...' : 'Ariza topshirish' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
