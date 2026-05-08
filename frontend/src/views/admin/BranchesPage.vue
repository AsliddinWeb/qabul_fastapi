<script setup lang="ts">
import { Building2 } from 'lucide-vue-next'
import SimpleCatalogPage from '@/components/admin/SimpleCatalogPage.vue'
import { adminApi } from '@/api/admin.api'
</script>

<template>
  <SimpleCatalogPage
    title="Filiallar"
    subtitle="Universitet filiallari (Toshkent, Andijon, Nukus, ...)"
    empty-title="Filiallar yo'q"
    :icon="Building2"
    :api="adminApi.branches"
    with-active
  />
</template>
