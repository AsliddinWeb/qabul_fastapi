<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="min-h-screen grid place-items-center bg-slate-50 dark:bg-slate-950 px-4 text-center">
    <div>
      <div class="text-7xl font-bold text-brand-600 dark:text-brand-400">404</div>
      <p class="mt-3 text-slate-600 dark:text-slate-400">Sahifa topilmadi.</p>
      <RouterLink to="/" class="btn-primary mt-6 inline-block">Bosh sahifaga qaytish</RouterLink>
    </div>
  </div>
</template>
