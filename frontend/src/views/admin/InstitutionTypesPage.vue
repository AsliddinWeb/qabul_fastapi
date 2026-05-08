<script setup lang="ts">
import { Building2 } from 'lucide-vue-next'
import SimpleCatalogPage from '@/components/admin/SimpleCatalogPage.vue'
import { adminApi } from '@/api/admin.api'
</script>

<template>
  <SimpleCatalogPage
    title="Muassasa turlari"
    subtitle="Universitet, Institut, Akademiya, Kollej, Litsey"
    empty-title="Muassasa turlari yo'q"
    :icon="Building2"
    :api="adminApi.institutionTypes"
  />
</template>
