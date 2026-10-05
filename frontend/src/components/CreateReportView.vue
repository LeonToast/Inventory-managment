<script setup lang="ts">
import { onMounted, ref } from 'vue'

const props = defineProps<{ accessToken: string }>()
const emit = defineEmits<{ back: []; created: [] }>()

type Warehouse = { id: string; name: string }

const reportTypes = [
  { value: 'inventory', label: 'Lageröversikt' },
  { value: 'deliveries', label: 'Leveransrapport' },
  { value: 'low_stock', label: 'Lågt lagersaldo' },
  { value: 'damaged', label: 'Skaderapport' },
  { value: 'capacity', label: 'Lagerutrymme' },
  { value: 'activity', label: 'Aktivitetsrapport' },
]
const dateString = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const today = new Date()
const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)
const reportType = ref('inventory')
const startDate = ref(dateString(startOfMonth))
const endDate = ref(dateString(today))
const warehouseId = ref('')
const description = ref('')
const warehouses = ref<Warehouse[]>([])
const loadingWarehouses = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const requestHeaders = () => ({ Authorization: `Bearer ${props.accessToken}` })

const loadWarehouses = async () => {
  loadingWarehouses.value = true
  errorMessage.value = ''
  try {
    const response = await fetch('http://127.0.0.1:8000/warehouse-capacity', { headers: requestHeaders() })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte hämta lagerlistan.')
    warehouses.value = result as Warehouse[]
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte hämta lagerlistan.'
  } finally {
    loadingWarehouses.value = false
  }
}

const createReport = async () => {
  if (endDate.value < startDate.value) {
    errorMessage.value = 'Slutdatumet måste vara samma dag eller senare än startdatumet.'
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    const response = await fetch('http://127.0.0.1:8000/reports', {
      method: 'POST',
      headers: { ...requestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        report_type: reportType.value,
        start_date: startDate.value,
        end_date: endDate.value,
        warehouse_id: warehouseId.value || null,
        description: description.value.trim(),
      }),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte skapa rapporten.')
    emit('created')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte skapa rapporten.'
  } finally {
    saving.value = false
  }
}

onMounted(loadWarehouses)
</script>

<template>
  <section class="create-report">
    <button class="back" type="button" @click="emit('back')">‹　Tillbaka till rapporter</button>
    <div class="form-heading">
      <div>
        <h1>Skapa rapport</h1>
        <p>Välj rapporttyp, datumperiod och lager. Rapporten sparas i rapportarkivet.</p>
      </div>
      <button class="primary" type="submit" form="create-report-form" :disabled="saving || loadingWarehouses">
        {{ saving ? 'Skapar rapport...' : 'Generera rapport' }}
      </button>
    </div>
    <form id="create-report-form" class="form-card report-form" @submit.prevent="createReport">
      <label>Rapporttyp
        <select v-model="reportType" required>
          <option v-for="type in reportTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
        </select>
      </label>
      <label>Lager
        <select v-model="warehouseId" :disabled="loadingWarehouses">
          <option value="">Alla lager</option>
          <option v-for="warehouse in warehouses" :key="warehouse.id" :value="warehouse.id">{{ warehouse.name }}</option>
        </select>
      </label>
      <label>Från och med
        <input v-model="startDate" type="date" required />
      </label>
      <label>Till och med
        <input v-model="endDate" type="date" :min="startDate" required />
      </label>
      <p class="report-period-note">Datum väljs i kalendern. Lageröversikt, lagersaldo, skador och lagerutrymme visar nuläget; leveranser och aktiviteter avgränsas av datumperioden.</p>
      <label class="report-description">Beskrivning
        <textarea v-model="description" maxlength="500" placeholder="Lägg till en kort beskrivning (valfritt)"></textarea>
      </label>
      <p v-if="errorMessage" class="report-form-error" role="alert">{{ errorMessage }}</p>
    </form>
  </section>
</template>
