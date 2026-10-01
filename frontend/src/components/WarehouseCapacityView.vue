<script setup lang="ts">
import WarehouseCapacityPanel from './WarehouseCapacityPanel.vue'

defineProps<{ isAdmin: boolean; accessToken: string }>()
const emit = defineEmits<{ 'open-materials': [] }>()
</script>

<template>
  <section class="warehouse-capacity-page">
    <div class="intro warehouse-capacity-intro">
      <div>
        <h1>Lagerutrymme</h1>
        <p>Följ uppmätt golvyta i varje lager och se hur mycket kapacitet som återstår.</p>
      </div>
    </div>
    <div class="warehouse-capacity-explanation">
      <strong>Så räknas utrymmet</strong>
      <p>
        Upptagen golvyta beräknas från varje artikels längd × bredd × lagersaldo.
        Stapling räknas inte med. Saknas mått visas den uppmätta ytan som ett minimum; exakt kvarvarande kapacitet visas först när alla material har mått.
      </p>
    </div>
    <WarehouseCapacityPanel :is-admin="isAdmin" :access-token="accessToken" @open-materials="emit('open-materials')" />
  </section>
</template>
