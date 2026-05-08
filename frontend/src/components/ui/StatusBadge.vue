<script setup lang="ts">
const props = defineProps<{ status: string; label?: string }>()

const styles: Record<string, string> = {
  draft:        'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  submitted:    'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  under_review: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  approved:     'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  accepted:     'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  rejected:     'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  cancelled:    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  contracted:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  enrolled:     'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  signed:       'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  completed:    'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  pending:      'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  confirmed:    'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  failed:       'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  refunded:     'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  two_party:    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  three_party:  'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
}

function cls(s: string): string {
  return styles[s] || 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
}
</script>

<template>
  <span class="text-xs px-2 py-1 rounded-full font-medium" :class="cls(props.status)">
    {{ props.label || props.status }}
  </span>
</template>
