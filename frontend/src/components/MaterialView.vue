<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ isAdmin: boolean }>()
const showMaterialModal = ref(false)
const materials = [
  { name: 'Kabeltrumma 25m', id: 'MAT-1024', tag: 'Elektronik', qty: '12', unit: 'st', a: 'Lager A · Sektion 3', b: 'Lager B · Sektion 2', av: '8 st', bv: '4 st', damaged: '1 st' },
  { name: 'Skyddshandskar', id: 'MAT-1180', tag: 'Förbrukning', qty: '248', unit: 'par', a: 'Lager B · Sektion 1', b: 'Lager C · Sektion 2', av: '180 par', bv: '68 par', damaged: '2 par' },
  { name: 'Pallställ 1200 kg', id: 'MAT-2042', tag: 'Utrustning', qty: '6', unit: 'st', a: 'Lager A · Sektion 5', b: '', av: '6 st', bv: '', damaged: '1 st' },
  { name: 'Fraktsedlar', id: 'MAT-2371', tag: 'Förbrukning', qty: '820', unit: 'st', a: 'Lager C · Sektion 2', b: 'Lager A · Sektion 2', av: '500 st', bv: '320 st', damaged: '2 st' },
]
</script>

<template>
  <section class="materials-page">
    <div class="intro material-intro">
      <div>
        <h1>Materiel</h1>
        <p>Material, förbrukning och utrustning i dina lager.</p>
      </div>
      <div class="material-actions"><span>●　8 skadade enheter · 6 artiklar totalt</span><button v-if="isAdmin"
          @click="showMaterialModal = true">＋　Lägg till material</button></div>
    </div>
    <div class="material-toolbar">
      <div class="search">⌕　 Sök efter namn, artikelnummer eller lagerplats</div><span>⚑　 Kategori</span>
      <nav><b>Alla</b><span>Förbrukning</span><span>Utrustning</span><span>Elektronik</span></nav><button>△　Skadade
        (8)</button>
    </div>
    <div class="material-heading"><b>Material</b><span>1–4 av 6　‹　›</span></div>
    <div class="material-grid">
      <article v-for="material in materials" :key="material.name" class="material-card">
        <div class="material-name"><i>◇</i>
          <div><b>{{ material.name }}</b><small>{{ material.id }} · 2 lager</small></div><em>{{ material.tag }}</em>
        </div>
        <hr><label>Fördelning per lager <strong>{{ material.qty }} <small>{{ material.unit }}</small></strong></label>
        <p>●　{{ material.a }} <b>{{ material.av }}</b></p>
        <p v-if="material.b">●　{{ material.b }} <b>{{ material.bv }}</b></p>
        <footer>△　Skadade enheter <b>{{ material.damaged }}</b></footer>
      </article>
    </div>
  </section>
  <div v-if="isAdmin && showMaterialModal" class="modal-backdrop" @click.self="showMaterialModal = false">
    <div class="material-modal"><button class="modal-close" @click="showMaterialModal = false">×</button>
      <div class="modal-icon">◇</div>
      <h2>Lägg till material</h2>
      <p>Registrera en ny artikel i ditt lager</p>
      <form @submit.prevent="showMaterialModal = false"><label class="full">Namn<input
            placeholder="Ex. Kabeltrumma 25m" /></label><label>Artikelnummer<input
            placeholder="MAT-0000" /></label><label>Kategori<select>
            <option>Förbrukning</option>
            <option>Elektronik</option>
            <option>Utrustning</option>
          </select></label><label>Lager<input placeholder="Ex. Lager A" /></label><label>Sektion<input
            placeholder="Ex. Sektion 1" /></label><label>Antal<input type="number"
            placeholder="0" /></label><label>Enhet<input placeholder="st, par" /></label><label>Skadade<input
            type="number" placeholder="0" /></label>
        <div class="modal-actions"><button type="button" @click="showMaterialModal = false">Avbryt</button><button
            type="submit">Spara material</button></div>
      </form>
    </div>
  </div>
</template>
