<script setup lang="ts">
/**
 * Reusable date-range filter with 4 presets (Bugun · Hafta · Oy · Custom).
 *
 * Two-way binds to `from` and `to` as YYYY-MM-DD strings, kept that way
 * because the URL filter layer (useUrlFilters) round-trips them to/from
 * the address bar and dates are URL-safest in their ISO short form.
 *
 * The two `<input type="date">` boxes show LOCAL dates to the user, but
 * `from`/`to` ship to the API as UTC-converted ISO timestamps via the
 * helpers `toApiFrom` / `toApiTo` exported here — call them when building
 * query params. This keeps the on-page UX in the user's timezone while
 * the server stores everything as UTC.
 *
 * The presets snap both ends to local-time midnight ↔ end-of-day:
 *   Bugun  → today 00:00 — today 23:59
 *   Hafta  → 7 days ago 00:00 — today 23:59
 *   Oy     → 30 days ago 00:00 — today 23:59
 *   Custom → whatever the user picked in the two date inputs
 *
 * Used by /admin/applications and /admin/leads. Add new modules by
 * binding the same v-model:from / v-model:to + calling toApiFrom/toApiTo
 * when shipping params.
 */
import { computed, ref, watch } from 'vue'
import { CalendarRange, X as XIcon } from 'lucide-vue-next'

interface Props {
  /** Inclusive lower bound (YYYY-MM-DD). Empty string = no lower bound. */
  from: string
  /** Inclusive upper bound (YYYY-MM-DD). Empty string = no upper bound. */
  to: string
  /** Label shown above the control. Defaults to "Sana oralig'i". */
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: "Sana oralig'i",
})

const emit = defineEmits<{
  'update:from': [value: string]
  'update:to':   [value: string]
}>()

type Preset = 'today' | 'week' | 'month' | 'custom' | null

// Helper: today's YYYY-MM-DD in local time. We can't use toISOString —
// that's UTC and would jump to tomorrow late at night in UZ.
function todayLocal(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function daysAgoLocal(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const today = todayLocal()

const activePreset = computed<Preset>(() => {
  if (!props.from && !props.to) return null
  if (props.from === today && props.to === today) return 'today'
  if (props.from === daysAgoLocal(6) && props.to === today) return 'week'
  if (props.from === daysAgoLocal(29) && props.to === today) return 'month'
  return 'custom'
})

function applyPreset(p: Preset) {
  if (p === 'today') {
    emit('update:from', today)
    emit('update:to', today)
  } else if (p === 'week') {
    emit('update:from', daysAgoLocal(6))
    emit('update:to', today)
  } else if (p === 'month') {
    emit('update:from', daysAgoLocal(29))
    emit('update:to', today)
  } else {
    // null / custom — clear both
    emit('update:from', '')
    emit('update:to', '')
  }
}

const customOpen = ref(false)
// Open the custom inputs automatically when there's already a custom range
// (e.g. URL-restored on page load). Don't reset to closed when the user
// switches to a preset — they may want to tweak it again afterwards.
watch(() => activePreset.value, (p) => {
  if (p === 'custom') customOpen.value = true
}, { immediate: true })

function clearAll() {
  emit('update:from', '')
  emit('update:to', '')
  customOpen.value = false
}

const hasValue = computed(() => !!(props.from || props.to))

const fromInput = computed<string>({
  get: () => props.from,
  set: (v) => emit('update:from', v),
})
const toInput = computed<string>({
  get: () => props.to,
  set: (v) => emit('update:to', v),
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <label class="field-label inline-flex items-center gap-1.5 !mb-0">
        <CalendarRange class="w-3.5 h-3.5" /> {{ label }}
      </label>
      <button v-if="hasValue" type="button"
              class="text-[11px] text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 inline-flex items-center gap-1"
              @click="clearAll">
        <XIcon class="w-3 h-3" /> Tozalash
      </button>
    </div>

    <div class="flex flex-wrap gap-1.5">
      <button type="button"
              class="px-3 py-1.5 text-xs font-semibold rounded-lg ring-1 transition"
              :class="activePreset === 'today'
                ? 'bg-brand-600 text-white ring-brand-600'
                : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800'"
              @click="applyPreset('today')">Bugun</button>

      <button type="button"
              class="px-3 py-1.5 text-xs font-semibold rounded-lg ring-1 transition"
              :class="activePreset === 'week'
                ? 'bg-brand-600 text-white ring-brand-600'
                : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800'"
              @click="applyPreset('week')">Hafta</button>

      <button type="button"
              class="px-3 py-1.5 text-xs font-semibold rounded-lg ring-1 transition"
              :class="activePreset === 'month'
                ? 'bg-brand-600 text-white ring-brand-600'
                : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800'"
              @click="applyPreset('month')">Oy</button>

      <button type="button"
              class="px-3 py-1.5 text-xs font-semibold rounded-lg ring-1 transition"
              :class="activePreset === 'custom'
                ? 'bg-brand-600 text-white ring-brand-600'
                : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800'"
              @click="customOpen = !customOpen">Boshqa…</button>
    </div>

    <div v-if="customOpen" class="mt-2 grid grid-cols-2 gap-2">
      <div>
        <label class="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">Dan</label>
        <input v-model="fromInput" type="date" class="input text-xs h-9" :max="toInput || today" />
      </div>
      <div>
        <label class="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">Gacha</label>
        <input v-model="toInput" type="date" class="input text-xs h-9" :min="fromInput || undefined" :max="today" />
      </div>
    </div>
  </div>
</template>
