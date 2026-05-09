<script setup lang="ts">
import AppHeader from '~/components/AppHeader.vue'
import AppFooter from '~/components/AppFooter.vue'
import LeadFormModal from '~/components/LeadFormModal.vue'

const { init } = useTheme()
onMounted(() => init())
</script>

<template>
  <div class="min-h-screen flex flex-col overflow-x-hidden">
    <AppHeader />
    <main class="flex-1 overflow-x-hidden">
      <slot />
    </main>
    <AppFooter />
    <LeadFormModal />
  </div>
</template>
