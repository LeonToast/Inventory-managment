import { computed, onUnmounted, ref, watch } from 'vue'

export const WARN_AFTER_MS = 15 * 60 * 1000
export const LOGOUT_AFTER_MS = 20 * 60 * 1000

const ACTIVITY_KEY = 'smart-lagring-last-activity'
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'scroll', 'touchstart'] as const
const THROTTLE_MS = 1000

/**
 * Warns after WARN_AFTER_MS without activity and calls onTimeout after LOGOUT_AFTER_MS.
 * Compares timestamps instead of using one long timer so it stays correct when the tab is
 * throttled or the computer sleeps, and shares the last activity time between tabs.
 */
export function useIdleTimeout(enabled: () => boolean, onTimeout: () => void) {
  const lastActivity = ref(Date.now())
  const now = ref(Date.now())
  let interval: ReturnType<typeof setInterval> | undefined

  const record = () => {
    lastActivity.value = now.value = Date.now()
    try {
      localStorage.setItem(ACTIVITY_KEY, String(lastActivity.value))
    } catch {
      // Storage unavailable: the timeout still works within this tab.
    }
  }
  const onActivity = () => {
    if (Date.now() - lastActivity.value >= THROTTLE_MS) record()
  }
  const onStorage = (event: StorageEvent) => {
    if (event.key === ACTIVITY_KEY && event.newValue) lastActivity.value = Number(event.newValue)
  }
  const tick = () => {
    now.value = Date.now()
    if (now.value - lastActivity.value >= LOGOUT_AFTER_MS) onTimeout()
  }

  const start = () => {
    record()
    for (const name of ACTIVITY_EVENTS) {
      document.addEventListener(name, onActivity, { capture: true, passive: true })
    }
    window.addEventListener('storage', onStorage)
    document.addEventListener('visibilitychange', tick)
    interval = setInterval(tick, 1000)
  }
  const stop = () => {
    for (const name of ACTIVITY_EVENTS) document.removeEventListener(name, onActivity, true)
    window.removeEventListener('storage', onStorage)
    document.removeEventListener('visibilitychange', tick)
    if (interval) clearInterval(interval)
    interval = undefined
  }

  watch(
    enabled,
    (isEnabled) => {
      stop()
      if (isEnabled) start()
    },
    { immediate: true },
  )
  onUnmounted(stop)

  const idleMs = computed(() => now.value - lastActivity.value)
  const showWarning = computed(() => enabled() && idleMs.value >= WARN_AFTER_MS)
  const secondsLeft = computed(() =>
    Math.max(0, Math.ceil((LOGOUT_AFTER_MS - idleMs.value) / 1000)),
  )
  return { showWarning, secondsLeft, dismissWarning: record }
}
