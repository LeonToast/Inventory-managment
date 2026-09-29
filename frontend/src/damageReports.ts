import { computed, ref } from 'vue'
import { apiJson } from './api'

export type DamageReport = {
  id: string
  material_id: string
  serial_number: string
  reported_at: string
}

export const damageReports = ref<DamageReport[]>([])
export const damageReportsLoaded = ref(false)
export const damageReportsError = ref('')
export const damagedCount = computed(() => damageReports.value.length)

let pendingLoad: Promise<void> | null = null

// Views that mount at the same time share one in-flight request.
export function loadDamageReports() {
  pendingLoad ??= apiJson<DamageReport[]>('/damage-reports', { authenticated: true })
    .then((reports) => {
      damageReports.value = reports
      damageReportsLoaded.value = true
      damageReportsError.value = ''
    })
    .catch((reason) => {
      damageReportsError.value =
        reason instanceof Error ? reason.message : 'Kunde inte hämta skador.'
    })
    .finally(() => {
      pendingLoad = null
    })
  return pendingLoad
}

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
