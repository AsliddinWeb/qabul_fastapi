<script setup lang="ts">
import { Layers } from 'lucide-vue-next'
import SimpleCatalogPage from '@/components/admin/SimpleCatalogPage.vue'
import { adminApi } from '@/api/admin.api'
</script>

<template>
  <SimpleCatalogPage
    title="Ta'lim darajalari"
    subtitle="Bakalavr, Magistr, ..."
    empty-title="Ta'lim darajalari yo'q"
    :icon="Layers"
    :api="adminApi.educationLevels"
  />
</template>
