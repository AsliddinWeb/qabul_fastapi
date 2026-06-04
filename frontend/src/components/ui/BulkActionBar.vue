<script setup lang="ts">
import { X as XIcon } from 'lucide-vue-next'

defineProps<{
  count: number
  label?: string
}>()
defineEmits<{ (e: 'clear'): void }>()
</script>

<template>
  <!-- Sticky bottom action bar — shows whenever count > 0. Slot lets each
       list inject its own buttons (Delete / Assign / Confirm / …) so the
       bar stays generic. -->
  <Transition
    enter-active-class="transition-all duration-200"
    leave-active-class="transition-all duration-150"
    enter-from-class="opacity-0 translate-y-3"
    leave-to-class="opacity-0 translate-y-3"
  >
    <div v-if="count > 0"
         class="sticky bottom-4 z-30 mt-4 mx-auto max-w-3xl
                rounded-2xl bg-slate-900/95 dark:bg-slate-100/95 text-white dark:text-slate-900
                shadow-2xl ring-1 ring-slate-800/30 dark:ring-slate-300/40
                backdrop-blur-md
                px-4 py-3 flex items-center gap-3 flex-wrap">
      <div class="flex items-center gap-2 min-w-0">
        <span class="inline-flex items-center justify-center min-w-[2rem] h-7 rounded-md text-sm font-bold tabular-nums px-2
                     bg-white/15 dark:bg-slate-900/15">
          {{ count }}
        </span>
        <span class="text-sm font-medium whitespace-nowrap">
          {{ label || 'ta tanlandi' }}
        </span>
      </div>

      <div class="flex items-center gap-1.5 ml-auto flex-wrap">
        <slot />
        <button type="button"
                class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                       bg-white/15 dark:bg-slate-900/15 hover:bg-white/25 dark:hover:bg-slate-900/25
                       transition"
                @click="$emit('clear')">
          <XIcon class="w-3 h-3" />
          Tozalash
        </button>
      </div>
    </div>
  </Transition>
</template>
