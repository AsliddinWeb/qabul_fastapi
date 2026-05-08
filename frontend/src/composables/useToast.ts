import { reactive } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'info'
  text: string
}

const state = reactive<{ items: Toast[] }>({ items: [] })
let nextId = 1

function show(text: string, type: Toast['type'] = 'success', duration = 3000) {
  const id = nextId++
  state.items.push({ id, text, type })
  setTimeout(() => {
    const idx = state.items.findIndex((t) => t.id === id)
    if (idx >= 0) state.items.splice(idx, 1)
  }, duration)
}

export function useToast() {
  return {
    items: state.items,
    success: (t: string) => show(t, 'success'),
    error:   (t: string) => show(t, 'error', 5000),
    info:    (t: string) => show(t, 'info'),
    dismiss: (id: number) => {
      const idx = state.items.findIndex((t) => t.id === id)
      if (idx >= 0) state.items.splice(idx, 1)
    },
  }
}
