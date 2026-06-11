<script setup lang="ts">
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

/**
 * Numbered pagination control.
 *
 * Every list page used to roll its own "‹ Oldingi · X / Y · Keyingi ›"
 * footer; the team wanted numbered page buttons so they can jump
 * around. This component renders:
 *
 *   ‹ Oldingi · [1] … [4] [5] [6] … [12] · Keyingi ›
 *
 * Show 1 and last always; show up to two neighbours of the current
 * page; insert ellipses for the gaps. Bind it with v-model:page.
 */
const props = defineProps<{
  page: number
  lastPage: number
  total?: number | null   // optional — shown as "Jami N ta" alongside
  size?: number | null    // page size (e.g. 20)
}>()
const emit = defineEmits<{ (e: 'update:page', v: number): void }>()

function go(p: number) {
  if (p < 1 || p > props.lastPage || p === props.page) return
  emit('update:page', p)
}

// Build the displayed pages array with -1 sentinels for ellipses.
const items = computed<Array<number | -1>>(() => {
  const total = props.lastPage
  const cur = props.page
  if (total <= 7) {
    // Small case: just show every page.
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  // Always include 1, last, current, current±1.
  const pages = new Set<number>([1, total, cur, cur - 1, cur + 1])
  // Also pull cur±2 so the window feels wide enough.
  pages.add(cur - 2); pages.add(cur + 2)
  const sorted = [...pages]
    .filter(p => p >= 1 && p <= total)
    .sort((a, b) => a - b)

  const out: Array<number | -1> = []
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) out.push(-1)
    out.push(sorted[i])
  }
  return out
})

// Display range for "N-M ko'rsatildi" caption.
const range = computed(() => {
  if (!props.total || !props.size) return null
  const start = (props.page - 1) * props.size + 1
  const end = Math.min(props.total, props.page * props.size)
  return { start, end, total: props.total }
})

function fmt(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}
</script>

<template>
  <nav v-if="lastPage > 1 || range"
       class="flex items-center justify-between flex-wrap gap-3 px-4 py-3 border-t border-slate-100 dark:border-slate-800">
    <!-- Range caption -->
    <div class="text-xs text-slate-500 dark:text-slate-400 tabular-nums">
      <template v-if="range">
        <strong class="text-slate-700 dark:text-slate-300">{{ fmt(range.start) }}–{{ fmt(range.end) }}</strong>
        <span class="text-slate-400 mx-1">/</span>
        <strong class="text-slate-700 dark:text-slate-300">{{ fmt(range.total) }}</strong>
      </template>
      <template v-else>
        Sahifa <strong class="text-slate-700 dark:text-slate-300">{{ page }}</strong> / {{ lastPage }}
      </template>
    </div>

    <!-- Page buttons -->
    <div v-if="lastPage > 1" class="flex items-center gap-1">
      <button type="button"
              class="inline-flex items-center justify-center w-8 h-8 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="page <= 1"
              :aria-label="'Oldingi sahifa'"
              @click="go(page - 1)">
        <ChevronLeft class="w-4 h-4" />
      </button>

      <template v-for="(it, i) in items" :key="`${it}-${i}`">
        <span v-if="it === -1"
              class="px-1 text-xs text-slate-400 select-none">…</span>
        <button v-else
                type="button"
                class="min-w-[2rem] h-8 px-2 rounded-md text-xs font-semibold tabular-nums transition"
                :class="it === page
                  ? 'bg-brand-500 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
                @click="go(it)">
          {{ it }}
        </button>
      </template>

      <button type="button"
              class="inline-flex items-center justify-center w-8 h-8 rounded-md text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="page >= lastPage"
              :aria-label="'Keyingi sahifa'"
              @click="go(page + 1)">
        <ChevronRight class="w-4 h-4" />
      </button>
    </div>
  </nav>
</template>
