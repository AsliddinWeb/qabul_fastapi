<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
import { Moon, Sun } from 'lucide-vue-next'

const theme = useThemeStore()
</script>

<template>
  <button
    class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
    :title="theme.isDark ? 'Kunduzgi rejim' : 'Tungi rejim'"
    :aria-label="theme.isDark ? 'Kunduzgi rejim' : 'Tungi rejim'"
    @click="theme.toggle"
  >
    <Sun v-if="theme.isDark" class="w-5 h-5" />
    <Moon v-else class="w-5 h-5" />
  </button>
</template>
