<script setup lang="ts">
import { CheckCircle2, XCircle, Info, X } from 'lucide-vue-next'
import { useToast } from '@/composables/useToast'

const toast = useToast()

const iconFor = (type: 'success' | 'error' | 'info') =>
  type === 'success' ? CheckCircle2 : type === 'error' ? XCircle : Info
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[100] space-y-2 pointer-events-none">
      <transition-group
        name="toast"
        enter-active-class="transition duration-200"
        enter-from-class="opacity-0 translate-x-2"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-for="t in toast.items"
          :key="t.id"
          class="pointer-events-auto card px-4 py-3 shadow-lg border min-w-[280px] max-w-md flex items-start gap-3"
          :class="{
            'border-green-200 dark:border-green-900': t.type === 'success',
            'border-red-200 dark:border-red-900': t.type === 'error',
            'border-slate-200 dark:border-slate-800': t.type === 'info',
          }"
        >
          <component
            :is="iconFor(t.type)"
            class="w-5 h-5 mt-0.5 shrink-0"
            :class="{
              'text-green-600 dark:text-green-400': t.type === 'success',
              'text-red-600 dark:text-red-400': t.type === 'error',
              'text-slate-600 dark:text-slate-400': t.type === 'info',
            }"
          />
          <div class="flex-1 text-sm text-slate-900 dark:text-slate-100">{{ t.text }}</div>
          <button
            class="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            @click="toast.dismiss(t.id)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>
