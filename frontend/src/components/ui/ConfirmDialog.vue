<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'

const { state, confirm, cancel } = useConfirm()

function onKey(e: KeyboardEvent) {
  if (!state.request) return
  if (e.key === 'Escape') cancel()
  else if (e.key === 'Enter') confirm()
}
</script>

<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition duration-150"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-100"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="state.request"
        class="fixed inset-0 z-[110] bg-black/40 grid place-items-center p-4"
        @click.self="cancel"
        @keydown="onKey"
      >
        <div class="card p-6 w-full max-w-md shadow-2xl space-y-4" tabindex="-1" autofocus>
          <div class="flex items-start gap-3">
            <div
              class="w-10 h-10 rounded-full grid place-items-center shrink-0"
              :class="state.request.tone === 'danger'
                ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-300'
                : 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'"
            >
              <AlertTriangle class="w-5 h-5" />
            </div>
            <div class="flex-1 min-w-0">
              <h3 class="font-semibold text-slate-900 dark:text-slate-100">{{ state.request.title }}</h3>
              <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
                {{ state.request.message }}
              </p>
            </div>
          </div>
          <div class="flex justify-end gap-2 pt-2">
            <button class="btn-ghost" @click="cancel">{{ state.request.cancelLabel }}</button>
            <button
              class="btn-primary"
              :class="state.request.tone === 'danger' ? '!bg-red-600 hover:!bg-red-700' : ''"
              autofocus
              @click="confirm"
            >
              {{ state.request.confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>
