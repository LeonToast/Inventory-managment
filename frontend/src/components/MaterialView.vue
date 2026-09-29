<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  damagedCount,
  damageReports,
  damageReportsError,
  loadDamageReports,
  reportDamage,
} from '../damageReports'
import { materials } from '../data/materials'
const props = defineProps<{ isAdmin: boolean; openDamageOnMount?: boolean }>()
const showMaterialModal = ref(false)
const showDamageModal = ref(false)
const showDamagedOnly = ref(false)
const selectedMaterialId = ref('')
const serialNumber = ref('')
const reportError = ref('')
const submittingReport = ref(false)

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
  showDamagedOnly.value
    ? materials.filter((material) => serialsByMaterial.value.has(material.id))
    : materials,
)
const openDamageModal = () => {
  selectedMaterialId.value = ''
  serialNumber.value = ''
  reportError.value = ''
  showDamageModal.value = true
}
onMounted(() => {
  loadDamageReports()
  if (props.openDamageOnMount) openDamageModal()
})
const submitDamageReport = async () => {
  const normalizedSerial = serialNumber.value.trim().toUpperCase()
  if (!selectedMaterialId.value || !normalizedSerial) {
    reportError.value = 'Välj material och ange serienummer.'
    return
  }
  if (damageReports.value.some((report) => report.serial_number === normalizedSerial)) {
    reportError.value = 'Serienumret är redan rapporterat som skadat.'
    return
  }
  submittingReport.value = true
  try {
    await reportDamage(selectedMaterialId.value, normalizedSerial)
    showDamageModal.value = false
  } catch (reason) {
    reportError.value = reason instanceof Error ? reason.message : 'Kunde inte spara skadan.'
  } finally {
    submittingReport.value = false
  }
}
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
        <button type="button" @click="openDamageModal">△　Rapportera skada</button>
        <button v-if="isAdmin" type="button" @click="showMaterialModal = true">
          ＋　Lägg till material
        </button>
      </div>
    </div>
    <div class="material-toolbar">
      <div class="search">⌕　 Sök efter namn, artikelnummer eller lagerplats</div>
      <span>⚑　 Kategori</span>
      <nav><b>Alla</b><span>Förbrukning</span><span>Utrustning</span><span>Elektronik</span></nav>
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
            <b>{{ material.name }}</b
            ><small>{{ material.id }} · 2 lager</small>
          </div>
          <em>{{ material.tag }}</em>
        </div>
        <hr />
        <label
          >Fördelning per lager
          <strong
            >{{ material.qty }} <small>{{ material.unit }}</small></strong
          ></label
        >
        <p>
          ●　{{ material.a }} <b>{{ material.av }}</b>
        </p>
        <p v-if="material.b">
          ●　{{ material.b }} <b>{{ material.bv }}</b>
        </p>
        <footer>
          △　Skadade enheter
          <b>{{ serialsFor(material.id).length }} {{ material.unit }}</b>
        </footer>
        <div v-if="serialsByMaterial.has(material.id)" class="damage-serials">
          Serienummer: {{ serialsFor(material.id).join(', ') }}
        </div>
      </article>
    </div>
    <p v-if="damageReportsError" class="damage-error" role="alert">{{ damageReportsError }}</p>
    <p v-if="showDamagedOnly && !visibleMaterials.length" class="damage-empty">
      Inga skador har rapporterats.
    </p>
  </section>
  <div v-if="showDamageModal" class="modal-backdrop" @click.self="showDamageModal = false">
    <div
      class="material-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="damage-modal-title"
    >
      <button class="modal-close" type="button" aria-label="Stäng" @click="showDamageModal = false">
        ×
      </button>
      <div class="modal-icon">△</div>
      <h2 id="damage-modal-title">Rapportera skadat material</h2>
      <p>Ange vilket material och serienummer som är trasigt.</p>
      <form @submit.prevent="submitDamageReport">
        <label class="full"
          >Material
          <select v-model="selectedMaterialId" required>
            <option value="" disabled>Välj material</option>
            <option v-for="material in materials" :key="material.id" :value="material.id">
              {{ material.name }} ({{ material.id }})
            </option>
          </select>
        </label>
        <label class="full"
          >Serienummer
          <input v-model="serialNumber" maxlength="100" required placeholder="Ange serienummer" />
        </label>
        <p v-if="reportError" class="damage-error full" role="alert">{{ reportError }}</p>
        <div class="modal-actions">
          <button type="button" @click="showDamageModal = false">Avbryt</button>
          <button type="submit" :disabled="submittingReport">Rapportera skada</button>
        </div>
      </form>
    </div>
  </div>
  <div
    v-if="isAdmin && showMaterialModal"
    class="modal-backdrop"
    @click.self="showMaterialModal = false"
  >
    <div class="material-modal">
      <button class="modal-close" @click="showMaterialModal = false">×</button>
      <div class="modal-icon">◇</div>
      <h2>Lägg till material</h2>
      <p>Registrera en ny artikel i ditt lager</p>
      <form @submit.prevent="showMaterialModal = false">
        <label class="full">Namn<input placeholder="Ex. Kabeltrumma 25m" /></label
        ><label>Artikelnummer<input placeholder="MAT-0000" /></label
        ><label
          >Kategori<select>
            <option>Förbrukning</option>
            <option>Elektronik</option>
            <option>Utrustning</option>
          </select></label
        ><label>Lager<input placeholder="Ex. Lager A" /></label
        ><label>Sektion<input placeholder="Ex. Sektion 1" /></label
        ><label>Antal<input type="number" placeholder="0" /></label
        ><label>Enhet<input placeholder="st, par" /></label
        ><label>Skadade<input type="number" placeholder="0" /></label>
        <div class="modal-actions">
          <button type="button" @click="showMaterialModal = false">Avbryt</button
          ><button type="submit">Spara material</button>
        </div>
      </form>
    </div>
  </div>
</template>
