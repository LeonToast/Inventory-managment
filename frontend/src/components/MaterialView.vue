<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorText } from '../api'
import {
  damagedCount,
  damageReports,
  damageReportsError,
  loadDamageReports,
} from '../damageReports'
import {
  MATERIAL_CATEGORIES,
  loadMaterials,
  materials,
  materialsError,
  removeMaterial,
  type Material,
} from '../materials'
import { matchesSearch } from '../search'
import DamageReportModal from './DamageReportModal.vue'
import MaterialFormModal from './MaterialFormModal.vue'

const props = defineProps<{ isAdmin: boolean; openDamageOnMount?: boolean }>()

const showDamageModal = ref(props.openDamageOnMount ?? false)
const showMaterialModal = ref(false)
const editingMaterial = ref<Material | null>(null)
const notice = ref('')
const deleteError = ref('')

const searchQuery = ref('')
const CATEGORY_FILTERS = ['Alla', ...MATERIAL_CATEGORIES]
const selectedCategory = ref('Alla')
const showDamagedOnly = ref(false)

// Without a material the form adds a new one; with one it edits that material.
const openMaterialModal = (material: Material | null = null) => {
  editingMaterial.value = material
  notice.value = ''
  deleteError.value = ''
  showMaterialModal.value = true
}
const onMaterialSaved = (message: string) => {
  notice.value = message
  showMaterialModal.value = false
}
const deleteMaterial = async (material: Material) => {
  if (!window.confirm(`Ta bort ${material.name}?`)) return
  notice.value = ''
  deleteError.value = ''
  try {
    await removeMaterial(material.id)
    notice.value = `${material.name} togs bort.`
  } catch (reason) {
    deleteError.value = errorText(reason, 'Kunde inte ta bort materialet.')
  }
}

// Damage reports refer to a material by its id.
const serialsByMaterial = computed(() => {
  const serials = new Map<string, string[]>()
  for (const report of damageReports.value) {
    const list = serials.get(report.material_id)
    if (list) list.push(report.serial_number)
    else serials.set(report.material_id, [report.serial_number])
  }
  return serials
})
const serialsFor = (materialId: string) => serialsByMaterial.value.get(materialId) ?? []

const visibleMaterials = computed(() =>
  materials.value.filter(
    (material) =>
      (selectedCategory.value === 'Alla' || material.category === selectedCategory.value) &&
      (!showDamagedOnly.value || serialsFor(material.id).length) &&
      matchesSearch([material.name, material.warehouse], searchQuery.value),
  ),
)
const filtersActive = computed(
  () => selectedCategory.value !== 'Alla' || searchQuery.value.trim() !== '',
)

onMounted(() => {
  loadMaterials()
  loadDamageReports()
})
</script>

<template>
  <section class="materials-page">
    <div class="intro material-intro">
      <div>
        <h1>Materiel</h1>
        <p>Material, förbrukning och utrustning i dina lager.</p>
      </div>
      <div class="material-actions">
        <span>●　{{ damagedCount }} skadade enheter · {{ materials.length }} artiklar totalt</span>
        <button type="button" :disabled="!materials.length" @click="showDamageModal = true">
          △　Rapportera skada
        </button>
        <button v-if="isAdmin" type="button" @click="openMaterialModal()">
          ＋　Lägg till material
        </button>
      </div>
    </div>
    <div class="material-toolbar">
      <div class="search">
        <span aria-hidden="true">⌕</span>
        <input
          v-model="searchQuery"
          type="search"
          aria-label="Sök material"
          placeholder="Sök efter namn eller lagerplats"
        />
      </div>
      <span>⚑　 Kategori</span>
      <nav aria-label="Kategori">
        <button
          v-for="category in CATEGORY_FILTERS"
          :key="category"
          type="button"
          :aria-pressed="selectedCategory === category"
          @click="selectedCategory = category"
        >
          {{ category }}
        </button>
      </nav>
      <button
        type="button"
        :aria-pressed="showDamagedOnly"
        @click="showDamagedOnly = !showDamagedOnly"
      >
        △　Skadade ({{ damagedCount }})
      </button>
    </div>
    <div class="material-heading">
      <b>Material</b><span>{{ visibleMaterials.length }} av {{ materials.length }}</span>
    </div>
    <div class="material-grid">
      <article v-for="material in visibleMaterials" :key="material.id" class="material-card">
        <div class="material-name">
          <i>◇</i>
          <div>
            <b>{{ material.name }}</b>
            <small v-if="material.warehouse">1 lager</small>
          </div>
          <em>{{ material.category }}</em>
        </div>
        <hr />
        <label
          >{{ material.warehouse ? 'Fördelning per lager' : 'Antal' }}
          <strong
            >{{ material.quantity }} <small>{{ material.unit }}</small></strong
          >
        </label>
        <p v-if="material.warehouse">
          ●　{{ material.warehouse }}
          <b>{{ material.quantity }} {{ material.unit }}</b>
        </p>
        <footer>
          △　Skadade enheter
          <b>{{ serialsFor(material.id).length }} {{ material.unit }}</b>
        </footer>
        <div v-if="serialsFor(material.id).length" class="damage-serials">
          Serienummer: {{ serialsFor(material.id).join(', ') }}
        </div>
        <div v-if="isAdmin" class="card-actions">
          <button type="button" @click="openMaterialModal(material)">Redigera</button>
          <button type="button" class="danger" @click="deleteMaterial(material)">Ta bort</button>
        </div>
      </article>
    </div>
    <p v-if="notice" class="empty-message" role="status">{{ notice }}</p>
    <p v-if="materialsError" class="damage-error" role="alert">{{ materialsError }}</p>
    <p v-if="deleteError" class="damage-error" role="alert">{{ deleteError }}</p>
    <p v-if="damageReportsError" class="damage-error" role="alert">{{ damageReportsError }}</p>
    <p v-if="!materials.length && !materialsError" class="empty-message">
      Inget material har lagts till ännu.
      <template v-if="isAdmin">Använd "Lägg till material" för att registrera det första.</template>
    </p>
    <p v-else-if="!visibleMaterials.length" class="empty-message">
      {{ filtersActive ? 'Inget material matchar din sökning.' : 'Inga skador har rapporterats.' }}
    </p>
  </section>
  <DamageReportModal v-if="showDamageModal" @close="showDamageModal = false" />
  <MaterialFormModal
    v-if="isAdmin && showMaterialModal"
    :material="editingMaterial"
    @close="showMaterialModal = false"
    @saved="onMaterialSaved"
  />
</template>
