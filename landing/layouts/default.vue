<script setup lang="ts">
import AppHeader from '~/components/AppHeader.vue'
import AppFooter from '~/components/AppFooter.vue'
import LeadFormModal from '~/components/LeadFormModal.vue'

const { init } = useTheme()
onMounted(() => init())
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <AppHeader />
    <main class="flex-1">
      <slot />
    </main>
    <AppFooter />
    <LeadFormModal />
  </div>
</template>
