<script setup lang="ts">
import { GraduationCap } from 'lucide-vue-next'
import SimpleCatalogPage from '@/components/admin/SimpleCatalogPage.vue'
import { adminApi } from '@/api/admin.api'
</script>

<template>
  <SimpleCatalogPage
    title="Ta'lim turlari"
    subtitle="Bakalavr, Magistratura, O'rta-maxsus, ..."
    empty-title="Ta'lim turlari yo'q"
    :icon="GraduationCap"
    :api="adminApi.educationTypes"
  />
</template>
