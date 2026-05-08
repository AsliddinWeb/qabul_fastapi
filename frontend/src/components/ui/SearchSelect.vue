<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronDown, Check, X as XIcon, Search } from 'lucide-vue-next'

interface Item { id: string; label: string; sub?: string }

const props = defineProps<{
  modelValue: string
  options: Item[]
  placeholder?: string
  disabled?: boolean
  allowClear?: boolean
}>()

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const open = ref(false)
const search = ref('')
const root = ref<HTMLElement | null>(null)

const selected = computed(() => props.options.find((o) => o.id === props.modelValue) || null)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return props.options
  return props.options.filter((o) =>
    o.label.toLowerCase().includes(q) ||
    (o.sub || '').toLowerCase().includes(q),
  )
})

function pick(o: Item) {
  emit('update:modelValue', o.id)
  open.value = false
  search.value = ''
}

function clear() {
  emit('update:modelValue', '')
  search.value = ''
}

function toggle() {
  if (props.disabled) return
  open.value = !open.value
}

function onOutside(e: MouseEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) open.value = false
}
function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape') open.value = false
}

watch(open, (v) => {
  if (v) {
    setTimeout(() => {
      const input = root.value?.querySelector<HTMLInputElement>('input[data-search]')
      input?.focus()
    }, 10)
  }
})

onMounted(() => {
  document.addEventListener('mousedown', onOutside)
  document.addEventListener('keydown', onEsc)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onOutside)
  document.removeEventListener('keydown', onEsc)
})
</script>

<template>
  <div ref="root" class="relative">
    <button type="button"
            class="input flex items-center justify-between w-full text-left pr-9"
            :class="{ 'opacity-60 cursor-not-allowed': disabled }"
            :disabled="disabled"
            @click="toggle">
      <span v-if="selected" class="truncate text-slate-900 dark:text-slate-100">{{ selected.label }}</span>
      <span v-else class="truncate text-slate-400 dark:text-slate-500">{{ placeholder || '— tanlang —' }}</span>
      <span class="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
        <button v-if="allowClear && selected" type="button"
                class="p-0.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400"
                title="Tozalash"
                @click.stop="clear">
          <XIcon class="w-3.5 h-3.5" />
        </button>
        <ChevronDown class="w-4 h-4 text-slate-400 transition-transform" :class="{ 'rotate-180': open }" />
      </span>
    </button>

    <transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open"
           class="absolute z-30 mt-1 w-full rounded-xl bg-white dark:bg-slate-900
                  border border-slate-200 dark:border-slate-700 shadow-lg overflow-hidden">
        <div class="relative p-2 border-b border-slate-100 dark:border-slate-800">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
          <input data-search
                 v-model="search"
                 type="text"
                 class="w-full text-sm pl-8 pr-2 py-1.5 rounded-md bg-slate-50 dark:bg-slate-800
                        border border-transparent focus:border-slate-300 dark:focus:border-slate-600 outline-none
                        placeholder:text-slate-400"
                 placeholder="Qidirish..." />
        </div>
        <ul class="max-h-64 overflow-auto py-1">
          <li v-if="!filtered.length" class="px-3 py-2 text-xs text-slate-400 text-center">
            Topilmadi
          </li>
          <li v-for="o in filtered" :key="o.id">
            <button type="button"
                    class="w-full text-left flex items-start gap-2 px-3 py-2 text-sm
                           hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                    :class="o.id === modelValue ? 'bg-slate-50 dark:bg-slate-800' : ''"
                    @click="pick(o)">
              <Check class="w-3.5 h-3.5 mt-0.5 shrink-0"
                     :class="o.id === modelValue ? 'text-slate-700 dark:text-slate-300' : 'text-transparent'" />
              <span class="min-w-0 flex-1">
                <span class="block text-slate-900 dark:text-slate-100 truncate">{{ o.label }}</span>
                <span v-if="o.sub" class="block text-[11px] text-slate-500 dark:text-slate-400 truncate">{{ o.sub }}</span>
              </span>
            </button>
          </li>
        </ul>
      </div>
    </transition>
  </div>
</template>
