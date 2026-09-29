import { ref } from 'vue'
import { apiJson, apiRequest, errorText, shareInFlight } from './api'

export const ANNOUNCEMENT_CATEGORIES = ['Rapport', 'Viktigt', 'Driftinformation', 'Status'] as const

type NewAnnouncement = {
  title: string
  text: string
  category: (typeof ANNOUNCEMENT_CATEGORIES)[number]
}

// The server assigns the id and the time; announcements arrive newest first.
export type Announcement = NewAnnouncement & { id: string; created_at: string }

export const announcements = ref<Announcement[]>([])
export const announcementsLoaded = ref(false)
export const announcementsError = ref('')

// Views that mount at the same time share one in-flight request.
export const loadAnnouncements = shareInFlight(async () => {
  try {
    announcements.value = await apiJson<Announcement[]>('/announcements', { authenticated: true })
    announcementsLoaded.value = true
    announcementsError.value = ''
  } catch (reason) {
    announcementsError.value = errorText(reason, 'Kunde inte hämta meddelanden.')
  }
})

export async function addAnnouncement(announcement: NewAnnouncement) {
  const created = await apiJson<Announcement>('/announcements', {
    method: 'POST',
    authenticated: true,
    json: announcement,
  })
  announcements.value = [created, ...announcements.value]
  announcementsError.value = ''
  return created
}

export async function removeAnnouncement(id: string) {
  await apiRequest(`/announcements/${id}`, { method: 'DELETE', authenticated: true })
  announcements.value = announcements.value.filter((announcement) => announcement.id !== id)
}

export function clearAnnouncements() {
  announcements.value = []
  announcementsLoaded.value = false
  announcementsError.value = ''
}
