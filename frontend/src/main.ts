import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from '@/stores/theme'
import './styles/main.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// Apply persisted theme before mount to avoid flash.
useThemeStore(pinia).init()

app.use(router)
app.mount('#app')

// Register service worker (PWA) — only in production builds
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/app/sw.js', { scope: '/app/' }).catch(() => {
      /* SW registration failure is non-fatal */
    })
  })
}
