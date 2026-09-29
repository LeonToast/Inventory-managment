<script setup lang="ts">
import { ref } from 'vue'
import { errorText } from '../api'
import { damageReports, reportDamage } from '../damageReports'
import { materials } from '../materials'

const emit = defineEmits<{ close: [] }>()

const selectedMaterialId = ref('')
const serialNumber = ref('')
const error = ref('')
const submitting = ref(false)

const submit = async () => {
  const normalizedSerial = serialNumber.value.trim().toUpperCase()
  if (!selectedMaterialId.value || !normalizedSerial) {
    error.value = 'Välj material och ange serienummer.'
    return
  }
  if (damageReports.value.some((report) => report.serial_number === normalizedSerial)) {
    error.value = 'Serienumret är redan rapporterat som skadat.'
    return
  }
  submitting.value = true
  try {
    await reportDamage(selectedMaterialId.value, normalizedSerial)
    emit('close')
  } catch (reason) {
    error.value = errorText(reason, 'Kunde inte spara skadan.')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div
      class="material-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="damage-modal-title"
    >
      <button class="modal-close" type="button" aria-label="Stäng" @click="emit('close')">×</button>
      <div class="modal-icon">△</div>
      <h2 id="damage-modal-title">Rapportera skadat material</h2>
      <p>Ange vilket material och serienummer som är trasigt.</p>
      <form @submit.prevent="submit">
        <label class="full"
          >Material
          <select v-model="selectedMaterialId" required>
            <option value="" disabled>Välj material</option>
            <option v-for="material in materials" :key="material.id" :value="material.id">
              {{ material.name }}{{ material.warehouse ? ` (${material.warehouse})` : '' }}
            </option>
          </select>
        </label>
        <label class="full"
          >Serienummer
          <input v-model="serialNumber" maxlength="100" required placeholder="Ange serienummer" />
        </label>
        <p v-if="error" class="damage-error full" role="alert">{{ error }}</p>
        <div class="modal-actions">
          <button type="button" @click="emit('close')">Avbryt</button>
          <button type="submit" :disabled="submitting">Rapportera skada</button>
        </div>
      </form>
    </div>
  </div>
</template>
