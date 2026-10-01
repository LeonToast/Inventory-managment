<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

const props = defineProps<{ isAdmin: boolean; accessToken: string; compact?: boolean }>()

type WarehouseCapacity = {
  id: string
  name: string
  capacity_m2: number | null
  occupied_m2: number
  unmeasured_materials: number
  utilization_percent: number | null
  remaining_percent: number | null
}

const warehouses = ref<WarehouseCapacity[]>([])
const capacityDrafts = reactive<Record<string, number>>({})
const errorMessage = ref('')
const savingWarehouseId = ref('')

const requestHeaders = () => ({ Authorization: `Bearer ${props.accessToken}` })

const loadWarehouses = async () => {
  errorMessage.value = ''
  try {
    const response = await fetch('http://127.0.0.1:8000/warehouse-capacity', { headers: requestHeaders() })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte hämta lagerkapaciteten.')
    warehouses.value = result
    for (const warehouse of result as WarehouseCapacity[]) {
      if (!(warehouse.id in capacityDrafts) && warehouse.capacity_m2 !== null) {
        capacityDrafts[warehouse.id] = warehouse.capacity_m2
      }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Kunde inte hämta lagerkapaciteten.'
  }
}

const saveCapacity = async (warehouse: WarehouseCapacity) => {
  const capacity = capacityDrafts[warehouse.id]
  if (typeof capacity !== 'number' || !Number.isFinite(capacity) || capacity <= 0) {
    errorMessage.value = 'Kapaciteten måste vara större än 0 m².'
    return
  }
  savingWarehouseId.value = warehouse.id
  errorMessage.value = ''
  try {
    const response = await fetch(`http://127.0.0.1:8000/warehouse-capacity/${warehouse.id}`, {
      method: 'PATCH',
      headers: { ...requestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ capacity_m2: capacity }),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || `Kunde inte spara kapaciteten för ${warehouse.name}.`)
    await loadWarehouses()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : `Kunde inte spara kapaciteten för ${warehouse.name}.`
  } finally {
    savingWarehouseId.value = ''
  }
}

const barWidth = (warehouse: WarehouseCapacity) => `${Math.min(warehouse.utilization_percent ?? 0, 100)}%`
const formatPercent = (value: number) => new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 2 }).format(value)
const emit = defineEmits<{ 'open-capacity': []; 'open-materials': [] }>()

onMounted(loadWarehouses)
</script>

<template>
  <section class="warehouse-capacity-panel" :class="{ compact }">
    <header class="warehouse-capacity-heading">
      <div>
        <h2>{{ compact ? 'Lagerkapacitet' : 'Lagerutrymme' }}</h2>
        <p v-if="compact">Uppmätt golvyta och kvarvarande kapacitet.</p>
        <p v-else>Golvyta beräknad från längd × bredd per enhet och lagersaldo; stapling räknas inte med.</p>
      </div>
    </header>
    <p v-if="errorMessage" class="warehouse-capacity-error" role="alert">{{ errorMessage }}</p>
    <p v-else-if="warehouses.length === 0" class="warehouse-capacity-empty">Inga lager hittades.</p>
    <div v-for="warehouse in warehouses" :key="warehouse.id" class="warehouse-capacity-row" :class="{ 'capacity-incomplete': warehouse.unmeasured_materials > 0 }">
      <div class="warehouse-capacity-row-heading">
        <strong>{{ warehouse.name }}</strong>
        <span v-if="compact && warehouse.unmeasured_materials > 0 && typeof warehouse.utilization_percent === 'number'">
          Minst {{ formatPercent(warehouse.utilization_percent) }}% uppmätt
        </span>
        <span v-else-if="compact && typeof warehouse.remaining_percent === 'number'">
          {{ formatPercent(warehouse.remaining_percent) }}% kvar
        </span>
        <span v-else-if="compact && warehouse.unmeasured_materials">
          Mått saknas
        </span>
        <span v-else-if="warehouse.capacity_m2 !== null">
          {{ warehouse.unmeasured_materials > 0 ? 'Minst ' : '' }}{{ warehouse.occupied_m2.toLocaleString('sv-SE') }} av {{ warehouse.capacity_m2.toLocaleString('sv-SE') }} m² · {{ warehouse.unmeasured_materials > 0 ? 'minst ' : '' }}{{ formatPercent(warehouse.utilization_percent ?? 0) }}% uppmätt
        </span>
        <span v-else>Kapacitet saknas</span>
      </div>
      <div
        v-if="warehouse.capacity_m2 !== null && typeof warehouse.utilization_percent === 'number'"
        class="warehouse-capacity-track"
        role="progressbar"
        :aria-label="`${warehouse.unmeasured_materials > 0 ? 'Minst ' : ''}${formatPercent(warehouse.utilization_percent)}% av golvytan är uppmätt i ${warehouse.name}`"
        :aria-valuenow="Math.round(warehouse.utilization_percent ?? 0)"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <span :style="{ width: barWidth(warehouse) }" :class="{ over: (warehouse.utilization_percent ?? 0) > 100 }"></span>
      </div>
      <small v-if="compact && warehouse.capacity_m2 !== null && typeof warehouse.utilization_percent === 'number'">
        {{ warehouse.unmeasured_materials > 0 ? 'Minst ' : '' }}{{ warehouse.occupied_m2.toLocaleString('sv-SE') }} av {{ warehouse.capacity_m2.toLocaleString('sv-SE') }} m² uppmätt · {{ warehouse.unmeasured_materials > 0 ? 'minst ' : '' }}{{ formatPercent(warehouse.utilization_percent) }}%
      </small>
      <small v-if="warehouse.unmeasured_materials">
        <template v-if="compact">Mått saknas för {{ warehouse.unmeasured_materials }} material; värdet ovan är ett minimum.</template>
        <template v-else>{{ warehouse.unmeasured_materials }} material saknar mått; värdet och stapeln visar bara uppmätt golvyta.</template>
      </small>
      <form v-if="isAdmin && !compact" class="warehouse-capacity-form" @submit.prevent="saveCapacity(warehouse)">
        <label>
          Kapacitet (m²)
          <input v-model.number="capacityDrafts[warehouse.id]" type="number" min="0.01" step="0.01" required />
        </label>
        <button type="submit" :disabled="savingWarehouseId === warehouse.id">
          {{ savingWarehouseId === warehouse.id ? 'Sparar...' : 'Spara kapacitet' }}
        </button>
      </form>
    </div>
    <button
      v-if="!compact && isAdmin && warehouses.some(warehouse => warehouse.unmeasured_materials > 0)"
      class="warehouse-capacity-manage"
      type="button"
      @click="emit('open-materials')"
    >
      Komplettera mått på material ›
    </button>
    <button v-if="compact" class="warehouse-capacity-manage" type="button" @click="emit('open-capacity')">
      Visa lagerutrymme ›
    </button>
  </section>
</template>
