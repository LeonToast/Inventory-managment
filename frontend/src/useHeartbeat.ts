import { onUnmounted, watch } from 'vue'
import { apiRequest } from './api'

const HEARTBEAT_MS = 60 * 1000

/**
 * While enabled, tells the server once a minute that this user is still here, so the members
 * list can show who is online. Beats are skipped while paused (e.g. during the idle warning).
 */
export function useHeartbeat(enabled: () => boolean, paused: () => boolean) {
  let interval: ReturnType<typeof setInterval> | undefined

  const stop = () => {
    clearInterval(interval)
    interval = undefined
  }
  const beat = () => {
    if (!paused()) apiRequest('/heartbeat', { method: 'POST', authenticated: true }).catch(() => {})
  }

  watch(
    enabled,
    (isEnabled) => {
      stop()
      if (isEnabled) interval = setInterval(beat, HEARTBEAT_MS)
    },
    { immediate: true },
  )
  onUnmounted(stop)
}
