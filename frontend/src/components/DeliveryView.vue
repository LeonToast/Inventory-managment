<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

type InventoryItem = { id: string; sku: string; name: string; unit: string; quantity: number; damaged_count: number; location: string; warehouse: string }
type Shipment = { id: string; shipment_id: string; customer_name: string; customer_email: string; material_name: string; sku: string; quantity: number; unit: string; warehouse: string; status: string; created_at: string }

const props = defineProps<{ isAdmin: boolean; accessToken: string }>()
const showDeliveryModal = ref(false)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const searchQuery = ref('')
const statusFilter = ref('all')
const inventory = ref<InventoryItem[]>([])
const shipments = ref<Shipment[]>([])
const selectedReceipt = ref<Shipment | null>(null)
const newShipment = reactive({ customer_name: '', customer_email: '', material_id: '', quantity: 1 })

const availableInventory = computed(() => inventory.value.filter(item => item.quantity - item.damaged_count > 0))
const selectedInventory = computed(() => availableInventory.value.find(item => item.id === newShipment.material_id))
const availableQuantity = computed(() => selectedInventory.value ? selectedInventory.value.quantity - selectedInventory.value.damaged_count : 0)
const quantityError = computed(() => {
  const quantity = Number(newShipment.quantity)
  if (!Number.isInteger(quantity) || quantity < 1) return 'Ange ett antal på minst 1.'
  if (quantity > availableQuantity.value && selectedInventory.value) {
    return `Det finns bara ${availableQuantity.value} oskadade ${selectedInventory.value.unit} i ${selectedInventory.value.warehouse}. Minska antalet eller välj ett annat lager.`
  }
  return ''
})
const deliveryStatistics = computed(() => [
  { label: 'TOTALT', value: shipments.value.length, unit: 'leveranser' },
  { label: 'SKICKADE', value: shipments.value.filter(shipment => shipment.status === 'shipped').length, unit: 'leveranser' },
  { label: 'KLARA', value: shipments.value.filter(shipment => shipment.status === 'delivered').length, unit: 'leveranser' },
  { label: 'AVBRUTNA', value: shipments.value.filter(shipment => shipment.status === 'cancelled').length, unit: 'leveranser' },
])
const filteredShipments = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('sv-SE')
  return shipments.value.filter(shipment => {
    const matchesStatus = statusFilter.value === 'all' || shipment.status === statusFilter.value
    const searchableText = `${shipment.shipment_id} ${shipment.customer_name} ${shipment.customer_email} ${shipment.material_name} ${shipment.sku} ${shipment.warehouse}`.toLocaleLowerCase('sv-SE')
    return matchesStatus && searchableText.includes(query)
  })
})

const requestHeaders = () => ({ Authorization: `Bearer ${props.accessToken}` })
const loadDeliveries = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [inventoryResponse, shipmentsResponse] = await Promise.all([
      fetch('http://127.0.0.1:8000/materials', { headers: requestHeaders() }),
      fetch('http://127.0.0.1:8000/shipments', { headers: requestHeaders() }),
    ])
    const [inventoryData, shipmentsData] = await Promise.all([
      inventoryResponse.json().catch(() => null),
      shipmentsResponse.json().catch(() => null),
    ])
    if (!inventoryResponse.ok) throw new Error(inventoryData?.detail || 'Kunde inte hämta lagersaldon.')
    if (!shipmentsResponse.ok) throw new Error(shipmentsData?.detail || 'Kunde inte hämta leveranser.')
    inventory.value = inventoryData
    shipments.value = shipmentsData
    if (!newShipment.material_id) newShipment.material_id = availableInventory.value[0]?.id ?? ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte hämta leveranser.'
  } finally {
    isLoading.value = false
  }
}

const submitShipment = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  if (!selectedInventory.value || quantityError.value) {
    errorMessage.value = quantityError.value || 'Välj en artikel från lagret.'
    return
  }
  isSaving.value = true
  try {
    const response = await fetch('http://127.0.0.1:8000/shipments', {
      method: 'POST',
      headers: { ...requestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer_name: newShipment.customer_name.trim(),
        customer_email: newShipment.customer_email.trim() || null,
        material_id: newShipment.material_id,
        quantity: newShipment.quantity,
      }),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte skicka ordern.')
    shipments.value.unshift(result)
    selectedInventory.value.quantity -= newShipment.quantity
    successMessage.value = `${result.shipment_id} skickad från ${result.warehouse}. Lagersaldot är uppdaterat.`
    selectedReceipt.value = result
    Object.assign(newShipment, { customer_name: '', customer_email: '', material_id: availableInventory.value[0]?.id ?? '', quantity: 1 })
    showDeliveryModal.value = false
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte skicka ordern.'
  } finally {
    isSaving.value = false
  }
}

const shipmentStatusLabel = (status: string) => ({
  shipped: 'Skickad',
  delivered: 'Levererad',
  cancelled: 'Avbruten',
}[status] ?? status)
const shipmentStatusTone = (status: string) => ({
  shipped: 'blue',
  delivered: 'green',
  cancelled: 'gray',
}[status] ?? 'gray')

const updateShipmentStatus = async (shipment: Shipment, status: 'delivered' | 'cancelled') => {
  if (status === 'cancelled' && !window.confirm(`Avbryta ${shipment.shipment_id}? ${shipment.quantity} ${shipment.unit} återförs till ${shipment.warehouse}.`)) return
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await fetch(`http://127.0.0.1:8000/shipments/${shipment.id}/status`, {
      method: 'PATCH',
      headers: { ...requestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte uppdatera leveransen.')
    shipments.value = shipments.value.map(item => item.id === result.id ? result : item)
    if (status === 'cancelled') await loadDeliveries()
    successMessage.value = status === 'delivered'
      ? `${shipment.shipment_id} markerad som levererad.`
      : `${shipment.shipment_id} avbruten och varan återförd till ${shipment.warehouse}.`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte uppdatera leveransen.'
  }
}

const formatShipmentTime = (value: string) => new Intl.DateTimeFormat('sv-SE', {
  dateStyle: 'medium',
  timeStyle: 'short',
}).format(new Date(value))
const printReceipt = () => window.print()

onMounted(loadDeliveries)
</script>

<template>
  <section class="delivery-page">
    <div class="delivery-intro">
      <div>
        <h1>Utgående leveranser</h1>
        <p>Skicka kundorder från lagret och uppdatera saldot automatiskt.</p>
      </div><button v-if="isAdmin" :disabled="availableInventory.length === 0" @click="showDeliveryModal = true">＋　Skapa kundleverans</button>
    </div>
    <p v-if="successMessage" class="delivery-message delivery-success" role="status">{{ successMessage }}</p>
    <p v-if="errorMessage && !showDeliveryModal" class="delivery-message delivery-error" role="alert">{{ errorMessage }}</p>
    <div class="delivery-stats">
      <article v-for="statistic in deliveryStatistics" :key="statistic.label"><small>{{ statistic.label }}</small><b>{{
        statistic.value }}</b><span>{{ statistic.unit }}</span>
      </article>
    </div>
    <div class="delivery-filter">
      <label class="delivery-search"><span aria-hidden="true">⌕</span><input v-model="searchQuery" type="search" aria-label="Sök leveranser" placeholder="Sök order, kund, artikel eller lager" /></label>
      <label class="delivery-status-filter"><span>Status</span><select v-model="statusFilter" aria-label="Filtrera leveranser efter status"><option value="all">Alla</option><option value="shipped">Skickade</option><option value="delivered">Levererade</option><option value="cancelled">Avbrutna</option></select></label>
    </div>
    <article class="delivery-table">
      <header>
        <div><b>Senaste kundleveranser</b><small>Varje order visar källagret som lagersaldot drogs från.</small></div><span>{{ filteredShipments.length }} av {{ shipments.length }}</span>
      </header>
      <div class="table-head"><span>ORDER / KUND</span><span>ARTIKEL</span><span>KÄLLAGER</span><span>SKICKAD</span><span>STATUS</span></div>
      <p v-if="isLoading" class="delivery-empty" role="status">Hämtar leveranser...</p>
      <p v-else-if="filteredShipments.length === 0" class="delivery-empty">{{ shipments.length === 0 ? 'Inga kundleveranser ännu.' : 'Inga leveranser matchar filtret.' }}</p>
      <div class="delivery-row" v-for="shipment in filteredShipments" :key="shipment.id">
        <div class="supplier"><i>◇</i><span><b>{{ shipment.customer_name }}</b><small>{{ shipment.shipment_id }}<template v-if="shipment.customer_email"> · {{ shipment.customer_email }}</template></small></span></div>
        <span>{{ shipment.material_name }} · {{ shipment.quantity }} {{ shipment.unit }}<small class="shipment-sku">{{ shipment.sku }}</small></span>
        <span>{{ shipment.warehouse }}</span><span>{{ formatShipmentTime(shipment.created_at) }}</span>
        <div class="delivery-actions">
          <strong :class="shipmentStatusTone(shipment.status)">{{ shipmentStatusLabel(shipment.status) }}</strong>
          <button type="button" class="receipt-open-button" @click="selectedReceipt = shipment">Kvitto</button>
          <button v-if="isAdmin && shipment.status === 'shipped'" type="button" class="shipment-action-button" @click="updateShipmentStatus(shipment, 'delivered')">Markera klar</button>
          <button v-if="isAdmin && shipment.status === 'shipped'" type="button" class="shipment-cancel-button" @click="updateShipmentStatus(shipment, 'cancelled')">Avbryt</button>
        </div>
      </div>
    </article>
  </section>
  <div v-if="isAdmin && showDeliveryModal" class="modal-backdrop" @click.self="showDeliveryModal = false">
    <div class="delivery-modal">
      <button class="modal-close" type="button" aria-label="Stäng" @click="showDeliveryModal = false">×</button>
      <div class="modal-icon">◇</div>
      <h2>Skapa kundleverans</h2>
      <p>Ordern skickas direkt och dras från valt lagersaldo.</p>
      <form @submit.prevent="submitShipment">
        <label class="full">Kundens namn<input v-model="newShipment.customer_name" required maxlength="120" placeholder="Namn eller företag" /></label>
        <label class="full">Kundens e-post <small>(valfritt)</small><input v-model="newShipment.customer_email" type="email" placeholder="kund@foretag.se" /></label>
        <label class="full">Artikel och källager<select v-model="newShipment.material_id" required>
          <option disabled value="">Välj artikel från lager</option>
          <option v-for="item in availableInventory" :key="item.id" :value="item.id">{{ item.sku }} · {{ item.name }} · {{ item.warehouse }} · {{ item.quantity - item.damaged_count }} {{ item.unit }} tillgängliga</option>
        </select></label>
        <p v-if="selectedInventory" class="shipment-stock-note">Skickas från {{ selectedInventory.warehouse }} · {{ selectedInventory.location }}. {{ availableQuantity }} oskadade {{ selectedInventory.unit }} finns.</p>
        <label class="full">Antal<input v-model.number="newShipment.quantity" type="number" min="1" required :aria-invalid="Boolean(quantityError)" aria-describedby="shipment-quantity-error" /></label>
        <p v-if="quantityError" id="shipment-quantity-error" class="shipment-form-error" role="alert">{{ quantityError }}</p>
        <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>
        <div class="modal-actions"><button type="button" @click="showDeliveryModal = false">Avbryt</button><button type="submit" :disabled="isSaving || !selectedInventory || Boolean(quantityError)">{{ isSaving ? 'Skickar...' : 'Skicka order' }}</button></div>
      </form>
    </div>
  </div>
  <div v-if="selectedReceipt" class="receipt-backdrop" @click.self="selectedReceipt = null">
    <article class="receipt-modal" role="dialog" aria-modal="true" aria-labelledby="receipt-title">
      <div class="receipt-brand"><span>⬡</span><b>Smart Lagring</b></div>
      <p class="receipt-eyebrow">UTGÅENDE LEVERANS</p>
      <h2 id="receipt-title">Leveranskvitto</h2>
      <p class="receipt-number">{{ selectedReceipt.shipment_id }}</p>
      <div class="receipt-rule"></div>
      <dl class="receipt-details">
        <div><dt>Datum</dt><dd>{{ formatShipmentTime(selectedReceipt.created_at) }}</dd></div>
        <div><dt>Kund</dt><dd>{{ selectedReceipt.customer_name }}</dd></div>
        <div v-if="selectedReceipt.customer_email"><dt>E-post</dt><dd>{{ selectedReceipt.customer_email }}</dd></div>
        <div><dt>Artikel</dt><dd>{{ selectedReceipt.material_name }} <small>{{ selectedReceipt.sku }}</small></dd></div>
        <div><dt>Antal</dt><dd>{{ selectedReceipt.quantity }} {{ selectedReceipt.unit }}</dd></div>
        <div><dt>Skickad från</dt><dd>{{ selectedReceipt.warehouse }}</dd></div>
        <div><dt>Status</dt><dd><span class="receipt-status" :class="shipmentStatusTone(selectedReceipt.status)">{{ shipmentStatusLabel(selectedReceipt.status) }}</span></dd></div>
      </dl>
      <p class="receipt-footer">{{ selectedReceipt.status === 'cancelled' ? 'Leveransen avbröts och varorna återfördes till lagret.' : selectedReceipt.status === 'delivered' ? 'Leveransen är markerad som levererad.' : 'Leveransen är registrerad i Smart Lagring.' }}</p>
      <div class="receipt-actions">
        <button type="button" @click="selectedReceipt = null">Stäng</button>
        <button type="button" @click="printReceipt">Skriv ut / Spara som PDF</button>
      </div>
    </article>
  </div>
</template>
