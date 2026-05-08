<script setup lang="ts">
import { RouterView } from 'vue-router'
import { Sun, Moon, ArrowLeft } from 'lucide-vue-next'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()
</script>

<template>
  <div class="min-h-screen relative overflow-hidden flex items-center justify-center px-4 py-12
              bg-stone-50 dark:bg-zinc-950">
    <!-- Decorative background -->
    <div class="absolute -top-40 -left-40 w-[560px] h-[560px] rounded-full opacity-30 dark:opacity-20 blur-3xl pointer-events-none"
         style="background: radial-gradient(closest-side, rgb(99 102 241 / 0.40), transparent 70%);"></div>
    <div class="absolute -bottom-40 -right-40 w-[600px] h-[600px] rounded-full opacity-25 dark:opacity-15 blur-3xl pointer-events-none"
         style="background: radial-gradient(closest-side, rgb(245 158 11 / 0.35), transparent 70%);"></div>

    <!-- Subtle dot grid -->
    <div class="absolute inset-0 pointer-events-none opacity-40 dark:opacity-25"
         style="background-image: radial-gradient(circle, rgb(113 113 122 / 0.18) 1px, transparent 1.4px); background-size: 28px 28px; mask-image: radial-gradient(ellipse 70% 50% at 50% 30%, black, transparent 80%); -webkit-mask-image: radial-gradient(ellipse 70% 50% at 50% 30%, black, transparent 80%);"></div>

    <div class="w-full max-w-md relative">
      <div class="flex items-center justify-between mb-5">
        <a href="/" class="flex items-center gap-3 group">
          <span class="grid place-items-center w-11 h-11 rounded-xl text-white font-bold text-lg shadow-md transition-transform group-hover:scale-105"
                style="background: linear-gradient(135deg, rgb(67 56 202), rgb(99 102 241));">X</span>
          <div class="leading-tight">
            <div class="font-bold tracking-tight text-slate-900 dark:text-slate-100">Xalqaro innovatsion</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 -mt-0.5">universiteti</div>
          </div>
        </a>
        <button
          class="grid place-items-center w-9 h-9 rounded-full text-slate-500 dark:text-slate-300 hover:bg-slate-200/60 dark:hover:bg-slate-800/60 transition-colors"
          :title="theme.isDark ? 'Kunduzgi rejim' : 'Tungi rejim'"
          @click="theme.toggle"
        >
          <Sun v-if="theme.isDark" class="w-[17px] h-[17px]" />
          <Moon v-else class="w-[17px] h-[17px]" />
        </button>
      </div>

      <a
        href="/"
        class="inline-flex items-center gap-1.5 mb-4 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors"
      >
        <ArrowLeft class="w-3.5 h-3.5" />
        Bosh sahifaga qaytish
      </a>

      <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-xl ring-1 ring-slate-200/60 dark:ring-slate-800 p-7 sm:p-8">
        <RouterView />
      </div>

      <div class="mt-6 text-center text-xs text-slate-500 dark:text-slate-400">
        © {{ new Date().getFullYear() }} Xalqaro Innovatsion Universiteti
      </div>
    </div>
  </div>
</template>
