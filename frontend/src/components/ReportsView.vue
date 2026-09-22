<script setup lang="ts">
const emit = defineEmits<{ 'create-report': [] }>()
defineProps<{ isAdmin: boolean }>()
const announcements = [
  { title: 'Månadsrapport · Oktober', text: 'Sammanfattning av lagerstatus, leveranser och avvikelser för oktober.', date: '28 okt 2024', category: 'Rapport', tone: 'blue', featured: true },
  { title: 'Nya rutiner för inventering', text: 'Vi har uppdaterat rutinerna för inventering i alla lager. Läs igenom den nya checklistan.', date: '24 okt 2024', category: 'Viktigt', tone: 'amber' },
  { title: 'Systemunderhåll planerat', text: 'Systemet kommer att vara otillgängligt söndag 3 november mellan 02:00 och 04:00.', date: '21 okt 2024', category: 'Driftinformation', tone: 'purple' },
  { title: 'Lager B är fullt fungerande', text: 'Åtgärderna efter den senaste inventeringen är nu slutförda.', date: '18 okt 2024', category: 'Status', tone: 'green' },
]
</script>

<template>
  <section class="reports-page">
    <div class="reports-intro">
      <div>
        <h1>Rapporter</h1>
        <p>Håll dig uppdaterad med nyheter och viktig information.</p>
      </div><button v-if="isAdmin" @click="emit('create-report')">＋　Ny rapport</button>
    </div>
    <div class="reports-toolbar">
      <div>⌕　 Sök bland rapporter och meddelanden</div>
      <nav><b>Alla</b><span>Rapporter</span><span>Viktigt</span><span>Driftinformation</span></nav>
    </div>
    <div class="reports-heading"><b>Senaste meddelanden</b><span>4 meddelanden</span></div>
    <article v-for="announcement in announcements" :key="announcement.title" class="announcement"
      :class="{ featured: announcement.featured }"><i :class="announcement.tone">▤</i>
      <div>
        <div class="announcement-top"><span class="tag" :class="announcement.tone">{{ announcement.category
            }}</span><time>{{ announcement.date }}</time></div>
        <h2>{{ announcement.title }}</h2>
        <p>{{ announcement.text }}</p><a>Läs mer　›</a>
      </div>
    </article>
  </section>
</template>
