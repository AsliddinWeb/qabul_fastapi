<script setup lang="ts">
import { Layers } from 'lucide-vue-next'
import SimpleCatalogPage from '@/components/admin/SimpleCatalogPage.vue'
import { adminApi } from '@/api/admin.api'
</script>

<template>
  <SimpleCatalogPage
    title="Kurslar"
    subtitle="1-kurs, 2-kurs, ... — perevod uchun maqsadli kurs"
    empty-title="Kurslar yo'q"
    :icon="Layers"
    :api="adminApi.courses"
  />
</template>
