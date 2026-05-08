<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <div class="text-center py-20">
    <h1 class="text-2xl font-semibold">{{ route.meta.title || 'Sahifa' }}</h1>
    <p class="mt-2 text-slate-500">
      Bu sahifa keyingi fazada (Phase 7+) to'liq amalga oshiriladi.
    </p>
  </div>
</template>
