/**
 * Theme composable — light / dark only.
 *
 * Initial value: localStorage('xiu-theme') or OS preference fallback.
 * Toggle simply flips light↔dark.
 */
type Mode = 'light' | 'dark'

const STORAGE_KEY = 'xiu-theme'

export const useTheme = () => {
  const isDark = useState<boolean>('xiu-theme-dark', () => false)

  function apply(dark: boolean) {
    isDark.value = dark
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', dark)
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
    }
  }

  function init() {
    if (typeof window === 'undefined') return
    const saved = localStorage.getItem(STORAGE_KEY) as Mode | null
    if (saved === 'dark') apply(true)
    else if (saved === 'light') apply(false)
    else apply(window.matchMedia('(prefers-color-scheme: dark)').matches)
  }

  function toggle() {
    apply(!isDark.value)
  }

  return { isDark, init, toggle }
}
