<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

defineProps<{
  title: string
  subtitle?: string
  /** Breadcrumb crumbs from root → parent. Title is appended automatically. */
  crumbs?: Array<{ label: string; to?: string }>
}>()
</script>

<template>
  <div class="flex flex-wrap items-end justify-between gap-4 mb-6">
    <div class="min-w-0">
      <!-- Breadcrumb -->
      <nav v-if="crumbs && crumbs.length"
           class="flex items-center gap-1.5 text-[12px] text-slate-500 dark:text-slate-400 mb-1.5">
        <template v-for="(c, i) in crumbs" :key="i">
          <component :is="c.to ? RouterLink : 'span'"
                     v-bind="c.to ? { to: c.to } : {}"
                     class="hover:text-brand-600 dark:hover:text-brand-300 transition-colors truncate max-w-[160px]"
                     :class="c.to ? 'cursor-pointer' : ''">
            {{ c.label }}
          </component>
          <ChevronRight class="w-3 h-3 text-slate-400 dark:text-slate-600 shrink-0" />
        </template>
        <span class="text-brand-600 dark:text-brand-300 font-medium truncate">{{ title }}</span>
      </nav>

      <!-- Title -->
      <h1 class="text-[22px] sm:text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight truncate">
        {{ title }}
      </h1>
      <p v-if="subtitle" class="mt-1 text-sm text-slate-500 dark:text-slate-400">{{ subtitle }}</p>
    </div>

    <!-- Right-side action slot -->
    <div class="flex items-center gap-2 shrink-0">
      <slot />
    </div>
  </div>
</template>
