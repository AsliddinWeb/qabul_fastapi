<script setup lang="ts">
import { BookOpen } from 'lucide-vue-next'
import SimpleCatalogPage from '@/components/admin/SimpleCatalogPage.vue'
import { adminApi } from '@/api/admin.api'
</script>

<template>
  <SimpleCatalogPage
    title="Ta'lim shakllari"
    subtitle="Kunduzgi, Sirtqi, Kechki, Masofaviy"
    empty-title="Ta'lim shakllari yo'q"
    :icon="BookOpen"
    :api="adminApi.educationForms"
  />
</template>
