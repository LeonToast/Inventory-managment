import { ref } from 'vue'
import { apiJson, errorText, shareInFlight } from './api'
import { formatDate } from './format'

export type ActivityKind = 'damage' | 'report' | 'material'

// The server assigns everything and sends the five latest entries, newest first.
type Activity = {
  id: string
  kind: ActivityKind
  title: string
  description: string
  created_at: string
}

export const activities = ref<Activity[]>([])
export const activityLoaded = ref(false)
export const activityError = ref('')

// Views that mount at the same time share one in-flight request.
export const loadActivity = shareInFlight(async () => {
  try {
    activities.value = await apiJson<Activity[]>('/activity', { authenticated: true })
    activityLoaded.value = true
    activityError.value = ''
  } catch (reason) {
    activityError.value = errorText(reason, 'Kunde inte hämta aktivitet.')
  }
})

export function clearActivity() {
  activities.value = []
  activityLoaded.value = false
  activityError.value = ''
}

// "just nu", "2 min sedan", "1 tim sedan", "3 dagar sedan", and a date for anything older.
export function timeAgo(value: string, now: number) {
  const minutes = Math.floor((now - new Date(value).getTime()) / 60_000)
  if (minutes < 1) return 'just nu'
  if (minutes < 60) return `${minutes} min sedan`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} tim sedan`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} ${days === 1 ? 'dag' : 'dagar'} sedan`
  return formatDate(value)
}
