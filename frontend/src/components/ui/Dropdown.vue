<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ align?: 'left' | 'right'; width?: number }>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const menuEl = ref<HTMLElement | null>(null)
const pos = ref({ top: -9999, left: -9999 })

function toggle() {
  if (!open.value) {
    // Compute initial position synchronously BEFORE mount so the menu never flashes at (0,0).
    primePosition()
  }
  open.value = !open.value
}
function close() { open.value = false }

function primePosition() {
  if (!root.value) return
  const r = root.value.getBoundingClientRect()
  const menuW = props.width ?? 224 // default width matches w-56
  const menuH = 200 // safe estimate; refined after mount
  const align = props.align || 'right'
  let top = r.bottom + 6
  let left = align === 'right' ? r.right - menuW : r.left
  if (top + menuH > window.innerHeight - 8) top = r.top - menuH - 6
  if (top < 8) top = 8
  if (left < 8) left = 8
  if (left + menuW > window.innerWidth - 8) left = window.innerWidth - menuW - 8
  pos.value = { top, left }
}

function reposition() {
  if (!root.value || !menuEl.value) return
  const r = root.value.getBoundingClientRect()
  const menuW = props.width ?? (menuEl.value.offsetWidth || 224)
  const menuH = menuEl.value.offsetHeight || 200
  const align = props.align || 'right'
  let top = r.bottom + 6
  let left = align === 'right' ? r.right - menuW : r.left
  if (top + menuH > window.innerHeight - 8) top = r.top - menuH - 6
  if (top < 8) top = 8
  if (left < 8) left = 8
  if (left + menuW > window.innerWidth - 8) left = window.innerWidth - menuW - 8
  pos.value = { top, left }
}

function onOutside(e: MouseEvent) {
  if (!open.value) return
  const t = e.target as Node
  if (root.value && root.value.contains(t)) return
  if (menuEl.value && menuEl.value.contains(t)) return
  close()
}
function onEsc(e: KeyboardEvent) { if (e.key === 'Escape') close() }
function onScroll() { close() }

watch(open, async (v) => {
  if (v) {
    await nextTick()
    reposition()
    window.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', reposition)
  } else {
    window.removeEventListener('scroll', onScroll, true)
    window.removeEventListener('resize', reposition)
  }
})

onMounted(() => {
  document.addEventListener('mousedown', onOutside)
  document.addEventListener('keydown', onEsc)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onOutside)
  document.removeEventListener('keydown', onEsc)
  window.removeEventListener('scroll', onScroll, true)
  window.removeEventListener('resize', reposition)
})
</script>

<template>
  <div ref="root" class="relative inline-block">
    <div @click="toggle">
      <slot name="trigger" :open="open" />
    </div>
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-100 ease-out"
        enter-from-class="opacity-0 -translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition duration-75 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div
          v-if="open"
          ref="menuEl"
          class="fixed z-[100] rounded-xl bg-white shadow-lg ring-1 ring-black/5
                 dark:bg-slate-900 dark:ring-white/10 p-1.5"
          :class="{ 'w-56': !width }"
          :style="{ top: pos.top + 'px', left: pos.left + 'px', width: width ? width + 'px' : undefined }"
          @click="close"
        >
          <slot />
        </div>
      </transition>
    </Teleport>
  </div>
</template>
