import { computed, ref } from 'vue'
import { apiJson, errorText, shareInFlight } from './api'

type DamageReport = {
  id: string
  material_id: string
  serial_number: string
  reported_at: string
}

export const damageReports = ref<DamageReport[]>([])
export const damageReportsLoaded = ref(false)
export const damageReportsError = ref('')
export const damagedCount = computed(() => damageReports.value.length)

// Views that mount at the same time share one in-flight request.
export const loadDamageReports = shareInFlight(async () => {
  try {
    damageReports.value = await apiJson<DamageReport[]>('/damage-reports', { authenticated: true })
    damageReportsLoaded.value = true
    damageReportsError.value = ''
  } catch (reason) {
    damageReportsError.value = errorText(reason, 'Kunde inte hämta skador.')
  }
})

export async function reportDamage(materialId: string, serialNumber: string) {
  const report = await apiJson<DamageReport>('/damage-reports', {
    method: 'POST',
    authenticated: true,
    json: { material_id: materialId, serial_number: serialNumber },
  })
  damageReports.value = [report, ...damageReports.value]
  damageReportsLoaded.value = true
  damageReportsError.value = ''
}

export function clearDamageReports() {
  damageReports.value = []
  damageReportsLoaded.value = false
  damageReportsError.value = ''
}
