import { defineStore } from 'pinia'

const KEY = 'xiu.ui.sidebarCollapsed'

export const useUIStore = defineStore('ui', {
  state: () => ({
    sidebarCollapsed: localStorage.getItem(KEY) === '1',
  }),
  actions: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
      localStorage.setItem(KEY, this.sidebarCollapsed ? '1' : '0')
    },
    setSidebarCollapsed(v: boolean) {
      this.sidebarCollapsed = v
      localStorage.setItem(KEY, v ? '1' : '0')
    },
  },
})
