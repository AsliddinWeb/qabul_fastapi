<script setup lang="ts">
import { useRouteProgress } from '@/composables/useRouteProgress'

const { value, visible } = useRouteProgress()
</script>

<template>
  <!-- Thin top-of-viewport progress bar. `fixed` so it sits above the
       sticky header; `pointer-events-none` so it never blocks clicks. -->
  <div
    aria-hidden="true"
    class="fixed top-0 left-0 right-0 z-[60] pointer-events-none transition-opacity duration-200"
    :style="{ opacity: visible ? 1 : 0 }"
  >
    <div
      class="h-[3px] bg-gradient-to-r from-brand-400 via-brand-500 to-violet-500
             shadow-[0_0_10px_rgb(99,102,241,0.7)] transition-[width] duration-200 ease-out"
      :style="{ width: `${value}%` }"
    ></div>
  </div>
</template>
