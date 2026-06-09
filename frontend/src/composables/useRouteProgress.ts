/**
 * Top-of-page route progress bar (NProgress-style, no extra dependency).
 *
 * Why: every navigation between SPA pages was instantaneous-yet-silent —
 * operators couldn't tell that the click had registered, so the site
 * felt static. A thin animated bar at the top is the canonical UX cue
 * (YouTube, GitHub, etc.) and ~50 lines of code, no library.
 *
 * Singleton pattern: a single reactive state shared across whatever
 * components want to read it. RouteProgress.vue renders the bar; the
 * router guards in router/index.ts call start()/done() on every nav.
 */
import { ref } from 'vue'

const value = ref(0)            // 0..100 — current bar width %
const visible = ref(false)      // true while the bar is on-screen
let trickleId: number | null = null
let doneId: number | null = null

function clearTimers() {
  if (trickleId !== null) { window.clearInterval(trickleId); trickleId = null }
  if (doneId !== null) { window.clearTimeout(doneId); doneId = null }
}

function start() {
  clearTimers()
  visible.value = true
  // Kick off at ~10% so it's immediately obvious the click registered.
  value.value = 10
  // Slow, asymptotic creep toward 95% so it never visibly stalls if the
  // route takes a moment to resolve. Step shrinks as we get closer to
  // 95% so the bar decelerates.
  trickleId = window.setInterval(() => {
    if (value.value >= 95) return
    const remaining = 95 - value.value
    const step = Math.max(0.5, Math.min(remaining * 0.08, 5))
    value.value = Math.min(95, value.value + step)
  }, 200)
}

function done() {
  clearTimers()
  value.value = 100
  // After the bar completes, wait a beat for the user's eye to register
  // it, then fade out and reset.
  doneId = window.setTimeout(() => {
    visible.value = false
    doneId = window.setTimeout(() => {
      value.value = 0
      doneId = null
    }, 200)
  }, 200)
}

export function useRouteProgress() {
  return { value, visible, start, done }
}
