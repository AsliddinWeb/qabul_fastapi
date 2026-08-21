<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { AlertTriangle, User as UserIcon, GitBranch, FileText, ExternalLink } from 'lucide-vue-next'
import { APPLICATION_STATUS, tr } from '@/utils/labels'
import type { PhoneCheckResult } from '@/api/leads.api'

const props = defineProps<{
  result: PhoneCheckResult | null
  panelPrefix: string
}>()

const LEAD_STATUS: Record<string, string> = {
  open: 'Ochiq (jarayonda)',
  won:  'Arizaga aylantirilgan',
  lost: "Yo'qotilgan",
}

const hasLead = computed(() => !!props.result?.lead)
const apps = computed(() => props.result?.applications ?? [])
const show = computed(() => hasLead.value || apps.value.length > 0)

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
</script>

<template>
  <div v-if="show" class="space-y-2.5">
    <div class="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-300">
      <AlertTriangle class="w-4 h-4 shrink-0" />
      <span>Bu raqam allaqachon tizimda — boshqa operator ishlagan</span>
    </div>

    <!-- Existing lead card -->
    <RouterLink
      v-if="result?.lead"
      :to="`${panelPrefix}/leads/${result.lead.id}`"
      class="block rounded-xl p-3.5 ring-1 transition
             bg-amber-50 ring-amber-200 hover:ring-amber-300
             dark:bg-amber-500/10 dark:ring-amber-500/30 dark:hover:ring-amber-500/50">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">
            <GitBranch class="w-3.5 h-3.5" /> Varonkada
          </div>
          <div class="mt-1 font-semibold text-slate-900 dark:text-slate-100 truncate">
            {{ result.lead.full_name || '—' }}
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600 dark:text-slate-300">
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium
                         bg-white/70 dark:bg-slate-800/60 ring-1 ring-amber-200 dark:ring-amber-500/30">
              {{ tr(LEAD_STATUS, result.lead.status) }}
            </span>
            <span v-if="result.lead.pipeline_name" class="text-slate-500 dark:text-slate-400">
              {{ result.lead.pipeline_name }}<template v-if="result.lead.stage_name"> · <span class="font-medium text-slate-700 dark:text-slate-200">{{ result.lead.stage_name }}</span></template>
            </span>
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-500 dark:text-slate-400">
            <span v-if="result.lead.assigned_to_name" class="inline-flex items-center gap-1">
              <UserIcon class="w-3.5 h-3.5" />
              <span class="font-medium text-slate-700 dark:text-slate-200">{{ result.lead.assigned_to_name }}</span> operatorga biriktirilgan
            </span>
            <span v-if="result.lead.created_at">{{ fmtDate(result.lead.created_at) }}</span>
          </div>
        </div>
        <ExternalLink class="w-4 h-4 shrink-0 text-amber-500" />
      </div>
    </RouterLink>

    <!-- Existing application cards -->
    <RouterLink
      v-for="a in apps" :key="a.id"
      :to="`${panelPrefix}/applications/${a.id}`"
      class="block rounded-xl p-3.5 ring-1 transition
             bg-rose-50 ring-rose-200 hover:ring-rose-300
             dark:bg-rose-500/10 dark:ring-rose-500/30 dark:hover:ring-rose-500/50">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400">
            <FileText class="w-3.5 h-3.5" /> Ariza mavjud
          </div>
          <div class="mt-1 flex items-center gap-2 min-w-0">
            <span class="font-mono text-xs text-slate-500 dark:text-slate-400">{{ a.application_number }}</span>
            <span class="font-semibold text-slate-900 dark:text-slate-100 truncate">{{ a.applicant_full_name || '—' }}</span>
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600 dark:text-slate-300">
            <span class="inline-flex items-center rounded-full px-2 py-0.5 font-medium
                         bg-white/70 dark:bg-slate-800/60 ring-1 ring-rose-200 dark:ring-rose-500/30">
              {{ tr(APPLICATION_STATUS, a.status) }}
            </span>
            <span v-if="a.program_name" class="text-slate-500 dark:text-slate-400 truncate">{{ a.program_name }}</span>
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-500 dark:text-slate-400">
            <span v-if="a.operator_name" class="inline-flex items-center gap-1">
              <UserIcon class="w-3.5 h-3.5" />
              <span class="font-medium text-slate-700 dark:text-slate-200">{{ a.operator_name }}</span> kiritgan
            </span>
            <span v-if="a.created_at">{{ fmtDate(a.created_at) }}</span>
          </div>
        </div>
        <ExternalLink class="w-4 h-4 shrink-0 text-rose-500" />
      </div>
    </RouterLink>
  </div>
</template>
