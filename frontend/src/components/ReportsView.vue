<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
const emit = defineEmits<{ 'create-report': [] }>()
const props = defineProps<{ isAdmin: boolean; accessToken: string }>()
const searchQuery = ref('')
const categoryFilter = ref('Alla')
const expandedAnnouncementTitle = ref('')
type GeneratedReport = {
  id: string
  title: string
  report_type: string
  period: { start: string; end: string }
  warehouse: string
  description: string
  summary: Record<string, number>
  rows: Array<Record<string, unknown>>
  generated_at: string
}
const generatedReports = ref<GeneratedReport[]>([])
const reportsLoading = ref(false)
const reportsError = ref('')
const expandedReportId = ref('')

const loadGeneratedReports = async () => {
  reportsLoading.value = true
  reportsError.value = ''
  try {
    const response = await fetch('http://127.0.0.1:8000/reports', {
      headers: { Authorization: `Bearer ${props.accessToken}` },
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte hämta sparade rapporter.')
    generatedReports.value = result as GeneratedReport[]
  } catch (error) {
    reportsError.value = error instanceof Error ? error.message : 'Kunde inte hämta sparade rapporter.'
  } finally {
    reportsLoading.value = false
  }
}

const formatDate = (value: string) => {
  if (!value) return '—'
  return new Intl.DateTimeFormat('sv-SE', { day: 'numeric', month: 'short', year: 'numeric' })
    .format(new Date(`${value}T12:00:00`))
}

const formatCell = (value: unknown) => {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const reportColumns = (report: GeneratedReport) => Object.keys(report.rows[0] ?? {})

const summaryItems = (summary: Record<string, number>) => Object.entries(summary)
  .filter(([, value]) => typeof value === 'number')
  .map(([key, value]) => ({
    label: ({
      items: 'Artiklar',
      quantity: 'Enheter',
      damaged_count: 'Skadade',
      deliveries: 'Leveranser',
      warehouses: 'Lager',
      unmeasured_materials: 'Artiklar utan mått',
      activities: 'Aktiviteter',
    } as Record<string, string>)[key] ?? key,
    value: new Intl.NumberFormat('sv-SE').format(value),
  }))

onMounted(loadGeneratedReports)
const announcements = [
  { title: 'Månadsrapport · Oktober', text: 'Sammanfattning av lagerstatus, leveranser och avvikelser för oktober.', details: 'Månadsrapporten sammanfattar lagersaldon, skickade och genomförda leveranser samt registrerade avvikelser under perioden. Öppna rapportarkivet för att skapa en aktuell rapport med valda datum och lager.', date: '28 okt 2024', category: 'Rapport', tone: 'blue', featured: true },
  { title: 'Nya rutiner för inventering', text: 'Vi har uppdaterat rutinerna för inventering i alla lager. Läs igenom den nya checklistan.', details: 'Kontrollera artikelnummer och lagerplats, räkna både hela och skadade enheter och registrera avvikelser direkt i systemet. Se till att varje sektion är färdig innan inventeringen markeras som klar.', date: '24 okt 2024', category: 'Viktigt', tone: 'amber' },
  { title: 'Systemunderhåll planerat', text: 'Systemet kommer att vara otillgängligt söndag 3 november mellan 02:00 och 04:00.', details: 'Under underhållsfönstret kan du inte logga in eller uppdatera lageruppgifter. Spara eventuella ändringar i förväg och försök igen när underhållet är klart.', date: '21 okt 2024', category: 'Driftinformation', tone: 'purple' },
  { title: 'Lager B är fullt fungerande', text: 'Åtgärderna efter den senaste inventeringen är nu slutförda.', details: 'Inventeringsavvikelserna har granskats och de berörda lagersaldona har uppdaterats. Lager B är åter tillgängligt för ordinarie arbete.', date: '18 okt 2024', category: 'Status', tone: 'green' },
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
const filteredGeneratedReports = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('sv-SE')
  return generatedReports.value.filter(report =>
    `${report.title} ${report.report_type} ${report.warehouse} ${report.description} ${report.period.start} ${report.period.end}`
      .toLocaleLowerCase('sv-SE')
      .includes(query),
  )
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
    <div class="reports-heading generated-reports-heading">
      <b>Skapade rapporter</b><span>{{ filteredGeneratedReports.length }} av {{ generatedReports.length }} rapporter</span>
      <button type="button" :disabled="reportsLoading" @click="loadGeneratedReports">{{ reportsLoading ? 'Hämtar...' : 'Uppdatera ↻' }}</button>
    </div>
    <p v-if="reportsError" class="reports-error" role="alert">{{ reportsError }}</p>
    <p v-else-if="reportsLoading && generatedReports.length === 0" class="reports-empty" role="status">Hämtar sparade rapporter...</p>
    <p v-else-if="generatedReports.length === 0" class="reports-empty">Inga rapporter skapade ännu.</p>
    <p v-else-if="filteredGeneratedReports.length === 0" class="reports-empty">Inga sparade rapporter matchar din sökning.</p>
    <article v-for="report in filteredGeneratedReports" :key="report.id" class="generated-report">
      <div class="generated-report-heading">
        <div>
          <span class="tag blue">{{ report.title }}</span>
          <h2>{{ report.warehouse }}</h2>
          <p>{{ formatDate(report.period.start) }} – {{ formatDate(report.period.end) }} · Skapad {{ new Intl.DateTimeFormat('sv-SE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(report.generated_at)) }}</p>
          <p v-if="report.description">{{ report.description }}</p>
        </div>
        <button type="button" :aria-expanded="expandedReportId === report.id" @click="expandedReportId = expandedReportId === report.id ? '' : report.id">
          {{ expandedReportId === report.id ? 'Dölj innehåll' : 'Visa innehåll' }}
        </button>
      </div>
      <div class="generated-report-summary">
        <span v-for="item in summaryItems(report.summary)" :key="item.label"><small>{{ item.label }}</small><b>{{ item.value }}</b></span>
      </div>
      <div v-if="expandedReportId === report.id" class="generated-report-table-wrap">
        <p v-if="report.rows.length === 0" class="reports-empty">Rapporten innehåller inga poster för det valda urvalet.</p>
        <table v-else class="generated-report-table">
          <thead><tr><th v-for="key in reportColumns(report)" :key="key">{{ key.replaceAll('_', ' ') }}</th></tr></thead>
          <tbody>
            <tr v-for="(row, index) in report.rows.slice(0, 100)" :key="index">
              <td v-for="key in reportColumns(report)" :key="key">{{ formatCell(row[key]) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="report.rows.length > 100" class="report-row-limit">Visar 100 av {{ report.rows.length }} poster.</p>
      </div>
    </article>
    <div class="reports-heading"><b>Senaste meddelanden</b><span>{{ filteredAnnouncements.length }} av {{ announcements.length }} meddelanden</span></div>
    <p v-if="filteredAnnouncements.length === 0" class="reports-empty">Inga rapporter matchar din sökning.</p>
    <article v-for="announcement in filteredAnnouncements" :key="announcement.title" class="announcement"
      :class="{ featured: announcement.featured, 'announcement-expanded': expandedAnnouncementTitle === announcement.title }"
      ><i :class="announcement.tone">▤</i>
      <div>
        <div class="announcement-top"><span class="tag" :class="announcement.tone">{{ announcement.category
            }}</span><time>{{ announcement.date }}</time></div>
        <h2>{{ announcement.title }}</h2>
        <p>{{ announcement.text }}</p>
        <p v-if="expandedAnnouncementTitle === announcement.title" class="announcement-details">{{ announcement.details }}</p>
        <button
          class="announcement-read-more"
          type="button"
          :aria-expanded="expandedAnnouncementTitle === announcement.title"
          @click="expandedAnnouncementTitle = expandedAnnouncementTitle === announcement.title ? '' : announcement.title"
        >{{ expandedAnnouncementTitle === announcement.title ? 'Visa mindre ↑' : 'Läs mer　›' }}</button>
      </div>
    </article>
  </section>
</template>
