import { ref } from 'vue'
import { apiJson, apiRequest, errorText, shareInFlight } from './api'

export const MATERIAL_CATEGORIES = ['Förbrukning', 'Elektronik', 'Utrustning'] as const
export const WAREHOUSES = ['Lager A', 'Lager B', 'Lager C']
export const UNITS = ['st', 'par', 'm', 'kg', 'l', 'förp']

type NewMaterial = {
  name: string
  category: (typeof MATERIAL_CATEGORIES)[number]
  warehouse: string
  quantity: number
  unit: string
}

// The server assigns the id.
export type Material = NewMaterial & { id: string }

export const materials = ref<Material[]>([])
export const materialsLoaded = ref(false)
export const materialsError = ref('')

// Always asks the server for the list, and reports a failure in materialsError.
async function fetchMaterials() {
  try {
    materials.value = await apiJson<Material[]>('/materials', { authenticated: true })
    materialsLoaded.value = true
    materialsError.value = ''
  } catch (reason) {
    materialsError.value = errorText(reason, 'Kunde inte hämta material.')
  }
}

// Views that mount at the same time share one in-flight request.
export const loadMaterials = shareInFlight(fetchMaterials)

// The list is reloaded after every change so it always shows what is stored.
export async function addMaterial(material: NewMaterial) {
  const created = await apiJson<Material>('/materials', {
    method: 'POST',
    authenticated: true,
    json: material,
  })
  await fetchMaterials()
  return created
}

export async function updateMaterial(id: string, material: NewMaterial) {
  const updated = await apiJson<Material>(`/materials/${id}`, {
    method: 'PATCH',
    authenticated: true,
    json: material,
  })
  await fetchMaterials()
  return updated
}

export async function removeMaterial(id: string) {
  await apiRequest(`/materials/${id}`, { method: 'DELETE', authenticated: true })
  await fetchMaterials()
}

export function clearMaterials() {
  materials.value = []
  materialsLoaded.value = false
  materialsError.value = ''
}
