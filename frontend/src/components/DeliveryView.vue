<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ isAdmin: boolean }>()
const showDeliveryModal = ref(false)
const deliveryStatistics = [{ label: 'TOTALT', value: '6', unit: 'leveranser', badge: '+5', tone: 'green' }, { label: 'PÅ VÄG', value: '1', unit: 'leveranser', badge: 'Aktiv', tone: 'green' }, { label: 'MOTTAGNA', value: '3', unit: 'leveranser', badge: 'Klart', tone: 'green' }, { label: 'AVVIKELSER', value: '1', unit: 'att följa upp', badge: 'Åtgärd', tone: 'amber' }]
const deliveries = [
  { supplier: 'Nordic Supply AB', id: 'LEV-24018', warehouse: 'Lager A', content: 'Kabeltrumma 25m · 24 st', date: 'Idag, 11:30', status: 'På väg', tone: 'blue' },
  { supplier: 'Pack & Frakt Sverige', id: 'LEV-24017', warehouse: 'Lager C', content: 'Fraktsedlar · 820 st', date: 'Idag, 09:45', status: 'Mottagen', tone: 'green' },
  { supplier: 'ScanTech Nordic', id: 'LEV-24016', warehouse: 'Lager B', content: 'Streckkodsläsare · 18 st', date: 'Igår, 15:20', status: 'Avvikelse', tone: 'amber' },
  { supplier: 'Industripartner', id: 'LEV-24015', warehouse: 'Lager A', content: 'Pallställ · 6 st', date: 'Igår, 13:10', status: 'Planerad', tone: 'gray' },
  { supplier: 'Skydd & Arbete AB', id: 'LEV-24014', warehouse: 'Lager B', content: 'Skyddshandskar · 248 par', date: '12 okt, 10:00', status: 'Mottagen', tone: 'green' },
]
</script>

<template>
  <section class="delivery-page">
    <div class="delivery-intro">
      <div>
        <h1>Leveranser</h1>
        <p>Följ inkommande leveranser och deras status till dina lager.</p>
      </div><button v-if="isAdmin" @click="showDeliveryModal = true">＋　Registrera leverans</button>
    </div>
    <div class="delivery-stats">
      <article v-for="statistic in deliveryStatistics" :key="statistic.label"><small>{{ statistic.label }}</small><b>{{
        statistic.value }}</b><span>{{ statistic.unit }}</span><em :class="statistic.tone">{{ statistic.badge }}</em>
      </article>
    </div>
    <div class="delivery-filter">
      <div>⌕　 Sök leverans, leverantör eller lager</div><span>⚑　 Status</span>
      <nav><b>Alla</b><span>På väg</span><span>Mottagen</span><span>Avvikelse</span><span>Planerad</span></nav>
    </div>
    <article class="delivery-table">
      <header>
        <div><b>Senaste leveranser</b><small>Registrerade leveranser till dina lager.</small></div><span>6 av 6</span>
      </header>
      <div class="table-head"><span>LEVERANS</span><span>LAGER</span><span>INNEHÅLL</span><span>PLANERAD
          TID</span><span>STATUS</span></div>
      <div class="delivery-row" v-for="delivery in deliveries" :key="delivery.id">
        <div class="supplier"><i>◇</i><span><b>{{ delivery.supplier }}</b><small>{{ delivery.id }}</small></span></div>
        <span>{{ delivery.warehouse }}</span><span>{{ delivery.content }}</span><span>{{ delivery.date }}</span><strong
          :class="delivery.tone">{{
            delivery.status }}</strong>
      </div>
    </article>
  </section>
'  <div v-if="isAdmin && showDeliveryModal" class="modal-backdrop" @click.self="showDeliveryModal = false"><div class="delivery-modal"><button class="modal-close" @click="showDeliveryModal = false">×</button><div class="modal-icon">◇</div><h2>Registrera leverans</h2><p>Lägg till en inkommande leverans i lagersystemet</p><form @submit.prevent="showDeliveryModal = false"><label class="full">Leverantör<input autofocus placeholder="Ex. Nordic Supply AB" /></label><label>Lager<input placeholder="Ex. Lager A" /></label><label>Planerad tid<input type="datetime-local" /></label><label class="full">Innehåll<input placeholder="Ex. Kabeltrumma 25m · 24 st" /></label><label class="full">Status<select><option>Planerad</option><option>På väg</option><option>Mottagen</option><option>Avvikelse</option></select></label><div class="modal-actions"><button type="button" @click="showDeliveryModal = false">Avbryt</button><button type="submit">Spara leverans</button></div></form></div></div>'
</template>
