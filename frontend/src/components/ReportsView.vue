<script setup lang="ts">
import { computed, ref } from 'vue'
const emit = defineEmits<{ 'create-report': [] }>()
defineProps<{ isAdmin: boolean }>()
const searchQuery = ref('')
const categoryFilter = ref('Alla')
const announcements = [
  { title: 'Månadsrapport · Oktober', text: 'Sammanfattning av lagerstatus, leveranser och avvikelser för oktober.', date: '28 okt 2024', category: 'Rapport', tone: 'blue', featured: true },
  { title: 'Nya rutiner för inventering', text: 'Vi har uppdaterat rutinerna för inventering i alla lager. Läs igenom den nya checklistan.', date: '24 okt 2024', category: 'Viktigt', tone: 'amber' },
  { title: 'Systemunderhåll planerat', text: 'Systemet kommer att vara otillgängligt söndag 3 november mellan 02:00 och 04:00.', date: '21 okt 2024', category: 'Driftinformation', tone: 'purple' },
  { title: 'Lager B är fullt fungerande', text: 'Åtgärderna efter den senaste inventeringen är nu slutförda.', date: '18 okt 2024', category: 'Status', tone: 'green' },
]
const categoryFilters = [
  { label: 'Alla', category: 'Alla' },
  { label: 'Rapporter', category: 'Rapport' },
  { label: 'Viktigt', category: 'Viktigt' },
  { label: 'Driftinformation', category: 'Driftinformation' },
]
const filteredAnnouncements = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('sv-SE')
  return announcements.filter(announcement => {
    const matchesCategory = categoryFilter.value === 'Alla' || announcement.category === categoryFilter.value
    const searchableText = `${announcement.title} ${announcement.text} ${announcement.category} ${announcement.date}`.toLocaleLowerCase('sv-SE')
    return matchesCategory && searchableText.includes(query)
  })
})
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
      <label class="reports-search"><span aria-hidden="true">⌕</span><input v-model="searchQuery" type="search" aria-label="Sök bland rapporter och meddelanden" placeholder="Sök bland rapporter och meddelanden" /></label>
      <nav aria-label="Filtrera rapporter efter kategori">
        <button v-for="filter in categoryFilters" :key="filter.category" type="button" :class="{ selected: categoryFilter === filter.category }" :aria-pressed="categoryFilter === filter.category" @click="categoryFilter = filter.category">{{ filter.label }}</button>
      </nav>
    </div>
    <div class="reports-heading"><b>Senaste meddelanden</b><span>{{ filteredAnnouncements.length }} av {{ announcements.length }} meddelanden</span></div>
    <p v-if="filteredAnnouncements.length === 0" class="reports-empty">Inga rapporter matchar din sökning.</p>
    <article v-for="announcement in filteredAnnouncements" :key="announcement.title" class="announcement"
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
