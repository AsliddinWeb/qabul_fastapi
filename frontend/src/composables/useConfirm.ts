import { reactive } from 'vue'

export interface ConfirmRequest {
  title: string
  message: string
  confirmLabel: string
  cancelLabel: string
  tone: 'danger' | 'primary'
  resolve: (ok: boolean) => void
}

const state = reactive<{ request: ConfirmRequest | null }>({ request: null })

export function useConfirm() {
  function ask(opts: {
    title: string
    message: string
    confirmLabel?: string
    cancelLabel?: string
    tone?: 'danger' | 'primary'
  }): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      state.request = {
        title: opts.title,
        message: opts.message,
        confirmLabel: opts.confirmLabel || 'Ha',
        cancelLabel: opts.cancelLabel || 'Bekor qilish',
        tone: opts.tone || 'primary',
        resolve,
      }
    })
  }

  function confirm() {
    state.request?.resolve(true)
    state.request = null
  }

  function cancel() {
    state.request?.resolve(false)
    state.request = null
  }

  return { state, ask, confirm, cancel }
}
