<script setup lang="ts">
import { Globe } from 'lucide-vue-next'
import SimpleCatalogPage from '@/components/admin/SimpleCatalogPage.vue'
import { adminApi } from '@/api/admin.api'
</script>

<template>
  <SimpleCatalogPage
    title="Davlatlar"
    subtitle="Perevod diplomi uchun chet davlatlar (O'zbekiston, Qozog'iston, Rossiya, ...)"
    empty-title="Davlatlar yo'q"
    :icon="Globe"
    :api="adminApi.countries"
  />
</template>
