import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme'

function detectSystem(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(mode: ThemeMode) {
  if (typeof document === 'undefined') return
  const effective = mode === 'system' ? detectSystem() : mode
  const html = document.documentElement
  if (effective === 'dark') html.classList.add('dark')
  else html.classList.remove('dark')
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: (localStorage.getItem(STORAGE_KEY) as ThemeMode) || 'system',
  }),

  getters: {
    isDark: (s) => {
      if (s.mode === 'system') return detectSystem() === 'dark'
      return s.mode === 'dark'
    },
  },

  actions: {
    setMode(mode: ThemeMode) {
      this.mode = mode
      localStorage.setItem(STORAGE_KEY, mode)
      applyTheme(mode)
    },
    toggle() {
      this.setMode(this.isDark ? 'light' : 'dark')
    },
    init() {
      applyTheme(this.mode)
      // React to system theme change when in 'system' mode
      if (typeof window !== 'undefined' && window.matchMedia) {
        window
          .matchMedia('(prefers-color-scheme: dark)')
          .addEventListener('change', () => {
            if (this.mode === 'system') applyTheme('system')
          })
      }
    },
  },
})
