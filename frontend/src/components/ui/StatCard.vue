<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'
import { TrendingUp, TrendingDown } from 'lucide-vue-next'

type Tone = 'brand' | 'sky' | 'emerald' | 'amber' | 'rose' | 'violet' | 'slate'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    hint?: string
    icon?: Component
    /** Numeric trend percent. Positive = up, negative = down, null = none */
    trend?: number | null
    /** Suffix appended to trend pill, e.g. "vs last month" */
    trendHint?: string
    tone?: Tone
  }>(),
  { tone: 'brand' }
)

const TONE_BG: Record<Tone, string> = {
  brand:   'bg-brand-100 text-brand-600 dark:bg-brand-500/20 dark:text-brand-200',
  sky:     'bg-sky-100 text-sky-600 dark:bg-sky-500/20 dark:text-sky-200',
  emerald: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-200',
  amber:   'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-200',
  rose:    'bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-200',
  violet:  'bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-200',
  slate:   'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-200',
}

const trendUp = computed(() => (props.trend ?? 0) >= 0)
const trendStr = computed(() => {
  if (props.trend == null) return ''
  const abs = Math.abs(props.trend).toFixed(1).replace('.0', '')
  return `${trendUp.value ? '+' : '−'}${abs}%`
})
</script>

<template>
  <div class="stat-card group relative overflow-hidden card p-5 transition-all hover:shadow-lg">
    <div class="relative flex items-start justify-between gap-3">
      <div class="min-w-0 flex-1">
        <div class="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">{{ label }}</div>
        <div class="text-[28px] font-bold text-slate-900 dark:text-slate-100 leading-none tracking-tight tabular-nums">
          {{ value }}
        </div>
        <div v-if="trend != null || hint" class="mt-3 flex items-center gap-2">
          <span v-if="trend != null"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold tabular-nums"
                :class="trendUp
                  ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
                  : 'bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300'">
            <component :is="trendUp ? TrendingUp : TrendingDown" class="w-3 h-3" />
            {{ trendStr }}
          </span>
          <span v-if="hint || trendHint" class="text-[11px] text-slate-500 dark:text-slate-400">
            {{ trendHint || hint }}
          </span>
        </div>
      </div>

      <div v-if="icon"
           class="grid place-items-center w-12 h-12 rounded-full shrink-0"
           :class="TONE_BG[tone]">
        <component :is="icon" class="w-5 h-5" />
      </div>
    </div>
  </div>
</template>
