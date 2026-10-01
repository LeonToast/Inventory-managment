<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
const props = defineProps<{ isAdmin: boolean; accessToken: string }>()
const emit = defineEmits<{ 'materials-updated': [] }>()
const showMaterialModal = ref(false)
type Material = { id: string; sku: string; name: string; category: string; quantity: number; minimum_stock: number; status: string; unit: string; location: string; damaged_count: number; footprint_length_cm: number | null; footprint_width_cm: number | null }
const materials = ref<Material[]>([])
const searchQuery = ref('')
const categoryFilter = ref('Alla')
const statusFilter = ref('all')
const isLoading = ref(false)
const errorMessage = ref('')
const formError = ref('')
const editingFootprintId = ref('')
const footprintDraft = reactive({ length: 0, width: 0 })
const newMaterial = reactive({ name: '', sku: '', category: 'Förbrukning', warehouse: '', section: '', quantity: 1, unit: 'st', damaged_count: 0, footprint_length_cm: 0, footprint_width_cm: 0 })
const categories = computed(() => ['Alla', ...Array.from(new Set(materials.value.map(material => material.category).filter(Boolean))).sort((a, b) => a.localeCompare(b, 'sv'))])
const formatQuantity = (quantity: number) => new Intl.NumberFormat('sv-SE').format(quantity)
const displayUnit = (unit: string) => {
  const normalizedUnit = unit.trim()
  return !normalizedUnit || /^\d+(?:[.,]\d+)?$/.test(normalizedUnit) ? 'st' : normalizedUnit
}
const displayLocation = (location: string) => location.replace(/(?:^| · )(\d+)$/, (_, section: string) => ` · Sektion ${section}`).replace(/^ · /, '')
const requestHeaders = () => ({ Authorization: `Bearer ${props.accessToken}` })
const filteredMaterials = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('sv-SE')
  return materials.value.filter(material => {
    const status = material.status || (material.quantity <= material.minimum_stock ? 'low' : 'available')
    const matchesCategory = categoryFilter.value === 'Alla' || material.category === categoryFilter.value
    const matchesStatus = statusFilter.value === 'all'
      || (statusFilter.value === 'available' && status === 'available')
      || (statusFilter.value === 'low' && status === 'low')
      || (statusFilter.value === 'damaged' && material.damaged_count > 0)
    const searchableText = `${material.name} ${material.sku} ${material.location} ${material.category}`.toLocaleLowerCase('sv-SE')
    return matchesCategory && matchesStatus && searchableText.includes(query)
  })
})

const loadMaterials = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await fetch('http://localhost:8000/materials', {
      headers: { Authorization: `Bearer ${props.accessToken}` },
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte hämta material.')
    materials.value = result
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte hämta material.'
  } finally {
    isLoading.value = false
  }
}

const submitMaterial = async () => {
  formError.value = ''
  if (/^\d+(?:[.,]\d+)?$/.test(newMaterial.unit.trim())) {
    formError.value = 'Ange en enhet med text, till exempel st, par eller kg.'
    return
  }
  try {
    const response = await fetch('http://localhost:8000/materials', {
      method: 'POST',
      headers: {
        ...requestHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(newMaterial),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte spara material.')
    materials.value.unshift(result)
    emit('materials-updated')
    Object.assign(newMaterial, { name: '', sku: '', category: 'Förbrukning', warehouse: '', section: '', quantity: 1, unit: 'st', damaged_count: 0, footprint_length_cm: 0, footprint_width_cm: 0 })
    showMaterialModal.value = false
  } catch (error) {
    formError.value = error instanceof Error ? error.message : 'Kunde inte spara material.'
  }
}

const editFootprint = (material: Material) => {
  editingFootprintId.value = material.id
  footprintDraft.length = material.footprint_length_cm ?? 0
  footprintDraft.width = material.footprint_width_cm ?? 0
}

const saveFootprint = async (material: Material) => {
  errorMessage.value = ''
  try {
    const response = await fetch(`http://localhost:8000/materials/${material.id}/footprint`, {
      method: 'PATCH',
      headers: { ...requestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        footprint_length_cm: footprintDraft.length,
        footprint_width_cm: footprintDraft.width,
      }),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte spara materialets mått.')
    material.footprint_length_cm = result.footprint_length_cm
    material.footprint_width_cm = result.footprint_width_cm
    editingFootprintId.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte spara materialets mått.'
  }
}

onMounted(loadMaterials)
</script>

<template>
  <section class="materials-page">
    <div class="intro material-intro">
      <div>
        <h1>Materiel</h1>
        <p>Material, förbrukning och utrustning i dina lager.</p>
      </div>
      <div class="material-actions"><span>●　{{ materials.reduce((total, material) => total + material.damaged_count, 0) }} skadade enheter · {{ materials.length }} artiklar totalt</span><button v-if="isAdmin"
          @click="showMaterialModal = true">＋　Lägg till material</button></div>
    </div>
    <div class="material-toolbar">
      <label class="search"><span aria-hidden="true">⌕</span><input v-model="searchQuery" type="search" aria-label="Sök material" placeholder="Sök namn, artikelnummer eller lagerplats" /></label>
      <nav aria-label="Filtrera efter kategori">
        <button v-for="category in categories" :key="category" type="button" :class="{ selected: categoryFilter === category }" :aria-pressed="categoryFilter === category" @click="categoryFilter = category">{{ category }}</button>
      </nav>
      <label class="material-status-filter"><span>Status</span><select v-model="statusFilter" aria-label="Filtrera efter status">
        <option value="all">Alla statusar</option>
        <option value="available">Tillgänglig</option>
        <option value="low">Lågt saldo</option>
        <option value="damaged">Skadad</option>
      </select></label>
    </div>
    <div class="material-heading"><b>Material</b><span>{{ filteredMaterials.length }} av {{ materials.length }} artiklar</span></div>
    <p v-if="isLoading" role="status">Hämtar material...</p>
    <p v-else-if="errorMessage" role="alert">{{ errorMessage }}</p>
    <p v-else-if="filteredMaterials.length === 0">Inga material matchar filtren.</p>
    <div class="material-grid">
      <article v-for="material in filteredMaterials" :key="material.id" class="material-card">
        <div class="material-name"><i>◇</i>
          <div><b>{{ material.name }}</b><small>{{ material.sku }}</small></div><em>{{ material.category }}</em>
        </div>
        <hr><label>Antal i lager <strong>{{ formatQuantity(material.quantity) }} <small>{{ displayUnit(material.unit) }}</small></strong></label>
        <p>●　{{ displayLocation(material.location) }}</p>
        <footer>△　Skadade enheter <b>{{ formatQuantity(material.damaged_count) }} {{ displayUnit(material.unit) }}</b></footer>
        <div class="material-footprint">
          <span v-if="material.footprint_length_cm && material.footprint_width_cm">
            Golvyta per enhet: {{ material.footprint_length_cm }} × {{ material.footprint_width_cm }} cm
          </span>
          <span v-else>Golvyta per enhet: Mått saknas</span>
          <button v-if="isAdmin && editingFootprintId !== material.id" type="button" @click="editFootprint(material)">
            {{ material.footprint_length_cm && material.footprint_width_cm ? 'Ändra mått' : 'Ange mått' }}
          </button>
          <form v-if="isAdmin && editingFootprintId === material.id" class="material-footprint-form" @submit.prevent="saveFootprint(material)">
            <label>Längd (cm)<input v-model.number="footprintDraft.length" type="number" min="0.01" step="0.01" required /></label>
            <label>Bredd (cm)<input v-model.number="footprintDraft.width" type="number" min="0.01" step="0.01" required /></label>
            <button type="submit">Spara mått</button>
            <button type="button" @click="editingFootprintId = ''">Avbryt</button>
          </form>
        </div>
      </article>
    </div>
  </section>
  <div v-if="isAdmin && showMaterialModal" class="modal-backdrop" @click.self="showMaterialModal = false">
    <div class="material-modal"><button class="modal-close" @click="showMaterialModal = false">×</button>
      <div class="modal-icon">◇</div>
      <h2>Lägg till material</h2>
      <p>Registrera en ny artikel i ditt lager</p>
      <form @submit.prevent="submitMaterial"><label class="full">Namn<input v-model="newMaterial.name" required
        placeholder="Ex. Kabeltrumma 25m" /></label><label>Artikelnummer<input v-model="newMaterial.sku" required
        placeholder="MAT-0000" /></label><label>Kategori<select v-model="newMaterial.category">
            <option>Förbrukning</option>
            <option>Elektronik</option>
            <option>Utrustning</option>
          </select></label><label>Lager<input v-model="newMaterial.warehouse" required placeholder="Ex. Lager A" /></label><label>Sektion<input
            v-model="newMaterial.section" required placeholder="Ex. Sektion 1" /></label><label>Antal<input v-model.number="newMaterial.quantity" type="number"
            min="0" required placeholder="0" /></label><label>Enhet<input v-model="newMaterial.unit" required placeholder="st, par" /></label><label>Skadade<input
            v-model.number="newMaterial.damaged_count" type="number" min="0" placeholder="0" /></label>
        <p v-if="formError" class="login-error" role="alert">{{ formError }}</p>
        <label>Längd per enhet (cm)<input v-model.number="newMaterial.footprint_length_cm" type="number" min="0.01" step="0.01" required placeholder="Ex. 40" /></label><label>Bredd per enhet (cm)<input v-model.number="newMaterial.footprint_width_cm" type="number" min="0.01" step="0.01" required placeholder="Ex. 30" /></label>
        <div class="modal-actions"><button type="button" @click="showMaterialModal = false">Avbryt</button><button
            type="submit">Spara material</button></div>
      </form>
    </div>
  </div>
</template>
