<script setup lang="ts">
import type { FunctionalComponent } from 'vue'
import { Inbox } from 'lucide-vue-next'

defineProps<{
  title?: string
  subtitle?: string
  icon?: FunctionalComponent | string
}>()
</script>

<template>
  <div class="text-center py-12">
    <div v-if="typeof icon === 'string'" class="text-4xl mb-2">{{ icon }}</div>
    <component
      v-else
      :is="icon || Inbox"
      class="w-10 h-10 mx-auto mb-2 text-slate-400 dark:text-slate-500"
    />
    <div class="font-medium text-slate-700 dark:text-slate-300">
      {{ title || "Hech narsa topilmadi" }}
    </div>
    <div v-if="subtitle" class="mt-1 text-sm text-slate-500 dark:text-slate-400">
      {{ subtitle }}
    </div>
    <div class="mt-4">
      <slot />
    </div>
  </div>
</template>
