<script setup lang="ts">
import { computed } from 'vue'

type SkeletonType =
  | 'block'
  | 'text'
  | 'circle'
  | 'card'
  | 'list'
  | 'table'
  | 'detail'
  | 'form'
  | 'dashboard'
  | 'kanban'

const props = withDefaults(
  defineProps<{
    type?: SkeletonType
    rows?: number
    cols?: number
    height?: string
    width?: string
    rounded?: string
  }>(),
  {
    type: 'block',
    rows: 6,
    cols: 5,
    height: '',
    width: '',
    rounded: '',
  }
)

const blockStyle = computed(() => ({
  height: props.height || undefined,
  width: props.width || undefined,
}))

const blockClass = computed(() => [
  'skeleton',
  props.rounded || (props.type === 'circle' ? 'rounded-full' : 'rounded-md'),
])

const tableRows = computed(() => Array.from({ length: props.rows }))
const tableCols = computed(() => Array.from({ length: props.cols }))
</script>

<template>
  <!-- Base block / text / circle -->
  <div v-if="type === 'block' || type === 'text' || type === 'circle'"
       :class="blockClass"
       :style="blockStyle">
  </div>

  <!-- Card placeholder -->
  <div v-else-if="type === 'card'" class="card p-5 space-y-3">
    <div class="skeleton h-5 w-1/3 rounded-md" />
    <div class="skeleton h-3 w-1/2 rounded" />
    <div class="skeleton h-3 w-2/3 rounded" />
  </div>

  <!-- Generic list (rows of items) -->
  <div v-else-if="type === 'list'" class="card p-5 space-y-4">
    <div v-for="(_, i) in tableRows" :key="i" class="flex items-center gap-3">
      <div class="skeleton w-10 h-10 rounded-full shrink-0" />
      <div class="flex-1 space-y-2">
        <div class="skeleton h-3 w-1/3 rounded" />
        <div class="skeleton h-2.5 w-2/3 rounded" />
      </div>
      <div class="skeleton h-6 w-20 rounded-md hidden sm:block" />
    </div>
  </div>

  <!-- Table page (filters bar + table) -->
  <div v-else-if="type === 'table'" class="space-y-4">
    <div class="flex flex-wrap items-center gap-3">
      <div class="skeleton h-9 w-72 rounded-lg" />
      <div class="skeleton h-9 w-40 rounded-lg" />
      <div class="skeleton h-9 w-40 rounded-lg" />
      <div class="skeleton h-9 w-28 rounded-lg ml-auto" />
    </div>
    <div class="card overflow-hidden">
      <div class="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 grid gap-4"
           :style="{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }">
        <div v-for="(_, c) in tableCols" :key="`h-${c}`"
             class="skeleton h-3 rounded"
             :class="c === 0 ? 'w-24' : c === cols - 1 ? 'w-16 ml-auto' : 'w-20'" />
      </div>
      <div v-for="(_, r) in tableRows" :key="r"
           class="px-5 py-4 border-b border-slate-100 dark:border-slate-800/60 grid gap-4 items-center"
           :style="{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }">
        <div v-for="(_, c) in tableCols" :key="`r-${r}-${c}`" class="flex items-center gap-3">
          <div v-if="c === 0" class="skeleton w-9 h-9 rounded-full shrink-0" />
          <div class="flex-1 space-y-2">
            <div class="skeleton h-3 rounded"
                 :class="c === 0 ? 'w-3/4' : 'w-1/2'" />
            <div v-if="c === 0" class="skeleton h-2.5 w-1/2 rounded" />
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Detail page: header + 2-column body -->
  <div v-else-if="type === 'detail'" class="space-y-6">
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-4">
        <div class="skeleton w-20 h-20 rounded-2xl shrink-0" />
        <div class="space-y-3">
          <div class="skeleton h-6 w-72 rounded-md" />
          <div class="skeleton h-3.5 w-44 rounded" />
          <div class="skeleton h-3 w-56 rounded" />
        </div>
      </div>
      <div class="flex gap-2">
        <div class="skeleton h-10 w-32 rounded-xl" />
        <div class="skeleton h-10 w-32 rounded-xl" />
      </div>
    </div>
    <div class="grid lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 card p-6 space-y-5">
        <div class="skeleton h-5 w-40 rounded-md" />
        <div class="grid sm:grid-cols-2 gap-4">
          <div v-for="i in 8" :key="i" class="space-y-2">
            <div class="skeleton h-3 w-20 rounded" />
            <div class="skeleton h-9 w-full rounded-lg" />
          </div>
        </div>
      </div>
      <div class="space-y-6">
        <div class="card p-5 space-y-3">
          <div class="skeleton h-5 w-32 rounded" />
          <div class="skeleton h-3 w-full rounded" />
          <div class="skeleton h-3 w-3/4 rounded" />
          <div class="skeleton h-3 w-2/3 rounded" />
        </div>
        <div class="card p-5 space-y-4">
          <div class="skeleton h-5 w-32 rounded" />
          <div v-for="i in 4" :key="i" class="flex items-center gap-3">
            <div class="skeleton w-9 h-9 rounded-full shrink-0" />
            <div class="flex-1 space-y-2">
              <div class="skeleton h-3 w-1/2 rounded" />
              <div class="skeleton h-2.5 w-1/3 rounded" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Form page -->
  <div v-else-if="type === 'form'" class="space-y-6">
    <div class="space-y-2">
      <div class="skeleton h-7 w-64 rounded-md" />
      <div class="skeleton h-3.5 w-96 rounded" />
    </div>
    <div class="card p-6 space-y-5">
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div v-for="i in rows || 12" :key="i" class="space-y-2">
          <div class="skeleton h-3 w-24 rounded" />
          <div class="skeleton h-10 w-full rounded-lg" />
        </div>
      </div>
      <div class="pt-4 border-t border-slate-200 dark:border-slate-800 flex gap-2">
        <div class="skeleton h-10 w-32 rounded-lg" />
        <div class="skeleton h-10 w-24 rounded-lg" />
      </div>
    </div>
  </div>

  <!-- Dashboard page -->
  <div v-else-if="type === 'dashboard'" class="space-y-6">
    <div class="card p-6 space-y-3">
      <div class="skeleton h-3 w-24 rounded" />
      <div class="skeleton h-8 w-64 rounded-md" />
      <div class="skeleton h-3 w-1/2 rounded" />
    </div>
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="card p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="skeleton h-3 w-20 rounded" />
          <div class="skeleton w-8 h-8 rounded-lg" />
        </div>
        <div class="skeleton h-8 w-16 rounded-md" />
        <div class="skeleton h-2.5 w-24 rounded" />
        <div class="skeleton h-12 w-full rounded" />
      </div>
    </div>
    <div class="grid lg:grid-cols-3 gap-4">
      <div class="card p-5 lg:col-span-2 space-y-4">
        <div class="skeleton h-5 w-40 rounded-md" />
        <div class="skeleton h-64 w-full rounded-lg" />
      </div>
      <div class="card p-5 space-y-4">
        <div class="skeleton h-5 w-32 rounded-md" />
        <div class="skeleton h-64 w-full rounded-lg" />
      </div>
    </div>
    <div class="grid lg:grid-cols-2 gap-4">
      <div class="card p-5 space-y-4">
        <div class="skeleton h-5 w-32 rounded-md" />
        <div v-for="i in 5" :key="i" class="space-y-2">
          <div class="flex items-center justify-between">
            <div class="skeleton h-3 w-24 rounded" />
            <div class="skeleton h-3 w-12 rounded" />
          </div>
          <div class="skeleton h-2 w-full rounded-full" />
        </div>
      </div>
      <div class="card p-5 space-y-4">
        <div class="skeleton h-5 w-32 rounded-md" />
        <div v-for="i in 5" :key="i" class="flex items-center gap-3">
          <div class="skeleton w-9 h-9 rounded-lg shrink-0" />
          <div class="flex-1 space-y-2">
            <div class="skeleton h-3 w-1/2 rounded" />
            <div class="skeleton h-2.5 w-1/3 rounded" />
          </div>
          <div class="skeleton h-3 w-12 rounded" />
        </div>
      </div>
    </div>
  </div>

  <!-- Kanban board -->
  <div v-else-if="type === 'kanban'" class="space-y-4">
    <div class="flex items-center justify-between">
      <div class="skeleton h-7 w-48 rounded-md" />
      <div class="skeleton h-9 w-40 rounded-lg" />
    </div>
    <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
      <div v-for="i in 5" :key="i" class="card p-3 space-y-3">
        <div class="flex items-center justify-between">
          <div class="skeleton h-4 w-24 rounded" />
          <div class="skeleton h-5 w-8 rounded-md" />
        </div>
        <div v-for="j in 3" :key="j" class="rounded-xl bg-slate-100/60 dark:bg-slate-800/40 p-3 space-y-2">
          <div class="flex items-center gap-2">
            <div class="skeleton w-9 h-9 rounded-full shrink-0" />
            <div class="flex-1 space-y-1.5">
              <div class="skeleton h-3 w-3/4 rounded" />
              <div class="skeleton h-2.5 w-1/2 rounded" />
            </div>
          </div>
          <div class="skeleton h-2.5 w-2/3 rounded" />
        </div>
      </div>
    </div>
  </div>
</template>
