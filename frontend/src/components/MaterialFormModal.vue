<script setup lang="ts">
import { reactive, ref } from 'vue'
import { errorText } from '../api'
import {
  MATERIAL_CATEGORIES,
  UNITS,
  WAREHOUSES,
  addMaterial,
  updateMaterial,
  type Material,
} from '../materials'

// Adding a material starts with an empty form; editing one starts from its saved values.
const { material } = defineProps<{ material: Material | null }>()
const emit = defineEmits<{ close: []; saved: [message: string] }>()

const form = reactive({
  name: material?.name ?? '',
  category: material?.category ?? MATERIAL_CATEGORIES[0],
  warehouse: material?.warehouse ?? '',
  quantity: material ? String(material.quantity) : '',
  unit: material?.unit ?? 'st',
})
const error = ref('')
const submitting = ref(false)

const submit = async () => {
  submitting.value = true
  error.value = ''
  const values = { ...form, quantity: Number(form.quantity) }
  try {
    if (material) {
      const updated = await updateMaterial(material.id, values)
      emit('saved', `${updated.name} uppdaterades.`)
    } else {
      const created = await addMaterial(values)
      emit('saved', `${created.name} sparades.`)
    }
  } catch (reason) {
    error.value = errorText(reason, 'Kunde inte spara materialet.')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="material-modal">
      <button class="modal-close" @click="emit('close')">×</button>
      <div class="modal-icon">◇</div>
      <h2>{{ material ? 'Redigera material' : 'Lägg till material' }}</h2>
      <p>
        {{ material ? 'Ändra uppgifterna för artikeln' : 'Registrera en ny artikel i ditt lager' }}
      </p>
      <form @submit.prevent="submit">
        <label class="full"
          >Namn<input
            v-model="form.name"
            maxlength="100"
            required
            placeholder="Ex. Kabeltrumma 25m"
        /></label>
        <label
          >Kategori<select v-model="form.category" required>
            <option v-for="category in MATERIAL_CATEGORIES" :key="category" :value="category">
              {{ category }}
            </option>
          </select></label
        >
        <label
          >Lager
          <select v-model="form.warehouse">
            <option value="">Inget (valfritt)</option>
            <option v-for="warehouse in WAREHOUSES" :key="warehouse" :value="warehouse">
              {{ warehouse }}
            </option>
          </select></label
        >
        <label
          >Antal<input
            v-model="form.quantity"
            type="number"
            min="0"
            step="1"
            required
            placeholder="0"
        /></label>
        <label
          >Enhet
          <select v-model="form.unit" required>
            <option v-for="unit in UNITS" :key="unit" :value="unit">{{ unit }}</option>
          </select></label
        >
        <p v-if="error" class="damage-error full" role="alert">{{ error }}</p>
        <div class="modal-actions">
          <button type="button" @click="emit('close')">Avbryt</button>
          <button type="submit" :disabled="submitting">
            {{ material ? 'Spara ändringar' : 'Spara material' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
