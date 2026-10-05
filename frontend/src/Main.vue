<script setup lang="ts">
import { computed, ref, provide, onMounted, onUnmounted } from 'vue'
import MaterialView from './components/MaterialView.vue'
import DeliveryView from './components/DeliveryView.vue'
import AccountView from './components/AccountView.vue'
import ReportsView from './components/ReportsView.vue'
import CreateReportView from './components/CreateReportView.vue'
import LandingView from './components/LandingView.vue'
import SettingsView from './components/SettingsView.vue'
import WarehouseCapacityView from './components/WarehouseCapacityView.vue'
import WarehouseCapacityPanel from './components/WarehouseCapacityPanel.vue'
const showLanding = ref(true)
const showReportForm = ref(false)
const currentAccount = ref<{ name: string; email: string; role: string; access_token: string } | null>(null)
const profileImage = ref('')
const darkMode = ref(false)
const profileMenuOpen = ref(false)
const sidebarLogoutOpen = ref(false)
const currentTime = ref(new Date())
const timeLabel = computed(() => currentTime.value.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
let clockInterval: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  darkMode.value = false
  document.documentElement.dataset.theme = 'light'
  localStorage.removeItem('smart-lagring-dark-mode')
  clockInterval = setInterval(() => { currentTime.value = new Date() }, 1000)
})
onUnmounted(() => {
  if (clockInterval) clearInterval(clockInterval)
})
const normalizeRole = (role?: string) => role === 'Medlem' ? 'Worker' : (role ?? 'Worker')
const isAdmin = computed(() => normalizeRole(currentAccount.value?.role) === 'Admin')
const isWorker = computed(() => !isAdmin.value && !!currentAccount.value)
type ActivityLog = { id: string; action: string; actor_id: string; actor_name: string; actor_role: string; details: Record<string, unknown>; created_at: string }
type ActivityDetail = { label: string; value: string }
type ActivityItem = { id: string; title: string; description: string; time: string; actor: string; color: string; icon: string; details: ActivityDetail[] }
const recentActivities = ref<ActivityItem[]>([])
const activityLoading = ref(false)
const activityError = ref('')
const selectedActivity = ref<ActivityItem | null>(null)
const inventorySummary = ref<Array<{ quantity: number; damaged_count: number }>>([])
const inventorySummaryError = ref('')
const totalStockQuantity = computed(() => inventorySummary.value.reduce((total, item) => total + item.quantity, 0))
const damagedStockQuantity = computed(() => inventorySummary.value.reduce((total, item) => total + item.damaged_count, 0))
const activityDetailLabels: Record<string, string> = {
  shipment_id: 'Ordernummer',
  customer_name: 'Kund',
  material_name: 'Artikel',
  name: 'Artikel',
  sku: 'Artikelnummer',
  quantity: 'Antal',
  unit: 'Enhet',
  warehouse: 'Lager',
  location: 'Lagerplats',
  category: 'Kategori',
  message: 'Information',
}
const presentActivity = (entry: ActivityLog): ActivityItem => {
  const details = Object.entries(entry.details ?? {}).filter(([key]) => key !== 'event').map(([key, value]) => ({
    label: activityDetailLabels[key] ?? key,
    value: String(value),
  }))
  const detailValue = (key: string) => {
    const value = entry.details?.[key]
    return value === undefined || value === null ? '' : String(value).trim()
  }
  const shipment = detailValue('shipment_id')
  const customer = detailValue('customer_name')
  const material = detailValue('material_name') || detailValue('name')
  const sku = detailValue('sku')
  const warehouse = detailValue('warehouse')
  const action = {
    login: { title: 'Inloggning', color: 'blue', icon: '↪' },
    material_created: { title: 'Nytt material registrerat', color: 'purple', icon: '◇' },
    shipment_created: { title: 'Kundleverans skickad', color: 'blue', icon: '↗' },
    shipment_delivered: { title: 'Leverans markerad klar', color: 'green', icon: '✓' },
    shipment_cancelled: { title: 'Leverans avbruten', color: 'amber', icon: '×' },
  }[entry.action] ?? { title: 'Systemaktivitet', color: 'gray', icon: '·' }
  const description = entry.action === 'login'
    ? `${entry.actor_role || 'Användare'} · ${entry.actor_name || entry.actor_id || 'Okänd användare'}`
    : (entry.action === 'material_created'
      ? [material, sku, warehouse].filter(Boolean).join(' · ')
      : [shipment, customer, material, warehouse].filter(Boolean).join(' · '))
  const actorName = entry.actor_name || entry.actor_id || 'Okänd användare'
  return {
    id: entry.id,
    ...action,
    description,
    time: new Intl.DateTimeFormat('sv-SE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(entry.created_at)),
    actor: actorName.includes('@') ? (entry.actor_role || 'Användare') : actorName,
    details,
  }
}
const loadRecentActivities = async () => {
  const accessToken = currentAccount.value?.access_token
  if (!accessToken) return
  activityLoading.value = true
  activityError.value = ''
  try {
    const response = await fetch('http://127.0.0.1:8000/activity-history', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte hämta senaste aktivitet.')
    recentActivities.value = (result as ActivityLog[]).map(presentActivity)
  } catch (error) {
    activityError.value = error instanceof Error ? error.message : 'Kunde inte hämta senaste aktivitet.'
  } finally {
    activityLoading.value = false
  }
}
const loadInventorySummary = async () => {
  const accessToken = currentAccount.value?.access_token
  if (!accessToken) return
  inventorySummaryError.value = ''
  try {
    const response = await fetch('http://127.0.0.1:8000/materials', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail || 'Kunde inte hämta lagersaldot.')
    inventorySummary.value = result
  } catch (error) {
    inventorySummaryError.value = error instanceof Error ? error.message : 'Kunde inte hämta lagersaldot.'
  }
}
type SavedProfile = { name?: string; image?: string; darkMode?: boolean }
const profileStorageKey = (email: string) => `smart-lagring-profile:${email.toLowerCase()}`
const readSavedProfile = (email: string): SavedProfile => {
  try {
    const saved = JSON.parse(localStorage.getItem(profileStorageKey(email)) ?? '{}')
    return saved && typeof saved === 'object' ? saved as SavedProfile : {}
  } catch {
    return {}
  }
}
const persistProfile = () => {
  if (!currentAccount.value) return
  localStorage.setItem(profileStorageKey(currentAccount.value.email), JSON.stringify({
    name: currentAccount.value.name,
    image: profileImage.value,
    darkMode: darkMode.value,
  }))
}
const handleLogin = (account?: { name: string; email: string; role: string; access_token: string }) => {
  const loggedInAccount = account ?? { name: 'Worker', email: '', role: 'Worker', access_token: '' }
  const savedProfile = readSavedProfile(loggedInAccount.email)
  currentAccount.value = { ...loggedInAccount, name: savedProfile.name || loggedInAccount.name }
  profileImage.value = savedProfile.image || ''
  darkMode.value = savedProfile.darkMode === true
  document.documentElement.dataset.theme = darkMode.value ? 'dark' : 'light'
  currentAccount.value.role = normalizeRole(currentAccount.value.role)
  showLanding.value = false
  void loadRecentActivities()
  void loadInventorySummary()
}
const saveProfile = (profile: { name: string; image: string }) => {
  if (!currentAccount.value) return
  currentAccount.value = { ...currentAccount.value, name: profile.name.trim() }
  profileImage.value = profile.image
  persistProfile()
  localStorage.setItem('smart-lagring-account', JSON.stringify(currentAccount.value))
}
const updateTheme = (enabled: boolean) => {
  if (!currentAccount.value) return
  darkMode.value = enabled
  document.documentElement.dataset.theme = enabled ? 'dark' : 'light'
  persistProfile()
}
const handleLogout = () => {
  currentAccount.value = null
  profileImage.value = ''
  darkMode.value = false
  document.documentElement.dataset.theme = 'light'
  profileMenuOpen.value = false
  sidebarLogoutOpen.value = false
  showReportForm.value = false
  active.value = 'Hem'
  showLanding.value = true
  localStorage.removeItem('smart-lagring-account')
}
const pendingAccounts = ref<Array<{ name: string; email: string; submittedAt: string }>>([])
provide('pendingAccounts', pendingAccounts)
const active = ref('Hem')
const nav = computed(() => ['Hem', 'Materiel', 'Lagerutrymme', 'Leverans', ...(isAdmin.value ? ['Hantera konton'] : []), 'Rapporter', 'Inställningar'])
const navIcons: Record<string, string> = {
  Hem: '⌂',
  Materiel: '◇',
  Lagerutrymme: '▤',
  Leverans: '⌾',
  'Hantera konton': '♧',
  Rapporter: '▥',
  Inställningar: '⚙',
}
const navigate = (navigationItem: string) => {
  active.value = navigationItem
  showReportForm.value = false
  profileMenuOpen.value = false
  if (navigationItem === 'Hem') {
    void loadRecentActivities()
    void loadInventorySummary()
  }
}
const overviewStatistics = computed(() => [
  { label: 'TOTALT LAGER', value: totalStockQuantity.value.toLocaleString('sv-SE'), unit: 'enheter' },
  { label: 'ARTIKELTYPER', value: inventorySummary.value.length.toLocaleString('sv-SE'), unit: 'artiklar' },
  { label: 'SKADAT', value: damagedStockQuantity.value.toLocaleString('sv-SE'), unit: 'enheter' },
])
</script>
<template>
<LandingView v-if="showLanding" @login="handleLogin" />
<div v-else class="app" @click="profileMenuOpen = false; sidebarLogoutOpen = false">
    <aside>
      <div class="brand"><b>⬡</b><strong>Smart lagring</strong></div>
      <div class="menu"><small>MENY</small><button v-for="navigationItem in nav" :key="navigationItem" :title="navigationItem" :class="{ on: active === navigationItem }"
          @click="navigate(navigationItem)"><i>{{ navIcons[navigationItem] }}</i>{{ navigationItem }}<em
            v-if="navigationItem === 'Materiel'">{{ totalStockQuantity.toLocaleString('sv-SE') }}</em></button></div>
      <div class="sidebar-account" @keydown.esc="sidebarLogoutOpen = false">
        <button class="user" type="button" :aria-label="sidebarLogoutOpen ? 'Stäng kontomenyn' : 'Öppna kontomenyn'" aria-controls="sidebar-logout" :aria-expanded="sidebarLogoutOpen" @click.stop="sidebarLogoutOpen = !sidebarLogoutOpen; profileMenuOpen = false"><img v-if="profileImage" class="user-photo" :src="profileImage" alt="" /><span v-else>{{ currentAccount?.name.slice(0, 2).toUpperCase() }}</span><b>{{ currentAccount?.name }}<small>{{ currentAccount?.role }}</small></b><svg class="sidebar-account-caret" viewBox="0 0 12 12" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg></button>
        <button v-if="sidebarLogoutOpen" id="sidebar-logout" class="sidebar-logout" type="button" @click.stop="handleLogout">↪　Logga ut</button>
      </div>
    </aside>
    <main>
      <header><span class="crumb">Smart lagring　›　<strong>{{ active === 'Hem' ? 'Översikt' : active }}</strong></span>
        <div class="header-tools">
          <span class="header-time">◷　{{ timeLabel }}</span>
          <div class="account-menu" @keydown.esc="profileMenuOpen = false">
            <button class="account-trigger" type="button" aria-haspopup="menu" :aria-expanded="profileMenuOpen" @click.stop="profileMenuOpen = !profileMenuOpen; sidebarLogoutOpen = false">
              <img v-if="profileImage" class="avatar profile-avatar" :src="profileImage" alt="" />
              <span v-else class="avatar">{{ isAdmin ? 'AD' : 'AR' }}</span>
              <span class="account-name">{{ currentAccount?.name }}</span>
            </button>
            <div v-if="profileMenuOpen" id="account-menu" class="account-dropdown" role="menu">
              <span class="account-email">{{ currentAccount?.email }}</span>
              <button type="button" role="menuitem" @click="active = 'Inställningar'; showReportForm = false; profileMenuOpen = false">⚙　Inställningar</button>
              <button type="button" role="menuitem" @click="handleLogout">↪　Logga ut</button>
            </div>
          </div>
        </div>
      </header>
      <CreateReportView v-if="showReportForm && isAdmin" :access-token="currentAccount?.access_token ?? ''" @back="showReportForm = false; active = 'Rapporter'" @created="showReportForm = false; active = 'Rapporter'" />
      <DeliveryView v-else-if="active === 'Leverans'" :is-admin="isAdmin" :access-token="currentAccount?.access_token ?? ''" />
      <MaterialView v-else-if="active === 'Materiel'" :is-admin="isAdmin" :access-token="currentAccount?.access_token ?? ''" @materials-updated="loadInventorySummary" />
      <WarehouseCapacityView v-else-if="active === 'Lagerutrymme'" :is-admin="isAdmin" :access-token="currentAccount?.access_token ?? ''" @open-materials="navigate('Materiel')" />
      <AccountView v-else-if="active === 'Hantera konton' && isAdmin" :is-admin="isAdmin" />
      <ReportsView v-else-if="active === 'Rapporter'" :is-admin="isAdmin" :access-token="currentAccount?.access_token ?? ''" @create-report="showReportForm = true" />
      <SettingsView v-else-if="active === 'Inställningar' && currentAccount" :name="currentAccount.name" :email="currentAccount.email" :profile-image="profileImage" :dark-mode="darkMode" @save-profile="saveProfile" @update-theme="updateTheme" />


      <section v-else>
        <div class="intro">
          <div>
            <h1>Översikt</h1>
            <p>{{ isAdmin ? 'Välkommen tillbaka, Admin. Här är dagens sammanfattning.' : 'Välkommen tillbaka, arbetare. Här är dagens lagerstatus.' }}</p>
          </div><span>●　{{ isAdmin ? 'Alla system fungerar' : 'Lagret är aktivt och redo' }}</span>
        </div>
        <div class="stats">
          <article
            v-for="statistic in overviewStatistics"
            :key="statistic.label"><small>{{ statistic.label }}</small><b>{{ statistic.value }}</b> <span>{{ statistic.unit }}</span></article>
        </div>
        <p v-if="inventorySummaryError" class="activity-state activity-error" role="alert">{{ inventorySummaryError }}</p>
        <div class="grid">
          <div>
            <article class="card activity">
              <div class="title"><b>Senaste aktivitet</b><button class="activity-refresh" type="button" :disabled="activityLoading" @click="loadRecentActivities">{{ activityLoading ? 'Hämtar...' : 'Uppdatera ↻' }}</button></div>
              <p v-if="activityLoading && recentActivities.length === 0" class="activity-state" role="status">Hämtar aktivitet...</p>
              <p v-else-if="activityError" class="activity-state activity-error" role="alert">{{ activityError }}</p>
              <p v-else-if="recentActivities.length === 0" class="activity-state">Ingen aktivitet registrerad ännu.</p>
              <button v-for="activity in recentActivities.slice(0, 4)" :key="activity.id" class="row activity-row" type="button" :aria-label="`Visa detaljer: ${activity.title}`" @click="selectedActivity = activity">
                <i :class="activity.color">{{ activity.icon }}</i>
                <span class="activity-copy"><b>{{ activity.title }}</b><small>{{ activity.description }}</small></span>
                <time>{{ activity.time }}</time><span class="activity-chevron" aria-hidden="true">›</span>
              </button>
            </article>
          </div>
          <div class="right">
            <article class="quick"><b>Snabbåtgärder</b><button v-if="isAdmin" @click="showReportForm = true">＋　Skapa rapport</button></article>
            <WarehouseCapacityPanel :is-admin="isAdmin" :access-token="currentAccount?.access_token ?? ''" compact @open-capacity="navigate('Lagerutrymme')" />
          </div>
        </div>
      </section>
    </main>
    <div v-if="selectedActivity" class="activity-details-backdrop" @click.self="selectedActivity = null">
      <section class="activity-details" role="dialog" aria-modal="true" aria-labelledby="activity-details-title">
        <button class="activity-details-close" type="button" aria-label="Stäng" @click="selectedActivity = null">×</button>
        <span class="activity-detail-icon" :class="selectedActivity.color">{{ selectedActivity.icon }}</span>
        <p class="activity-detail-type">Aktivitet</p>
        <h2 id="activity-details-title">{{ selectedActivity.title }}</h2>
        <p class="activity-detail-description">{{ selectedActivity.description }}</p>
        <dl>
          <div><dt>Utförd av</dt><dd>{{ selectedActivity.actor }}</dd></div>
          <div><dt>Tid</dt><dd>{{ selectedActivity.time }}</dd></div>
          <div v-for="detail in selectedActivity.details" :key="detail.label" :class="{ 'activity-detail-wide': detail.label === 'Information' }"><dt>{{ detail.label }}</dt><dd>{{ detail.value }}</dd></div>
        </dl>
      </section>
    </div>
    <button class="help">?</button>
  </div>
</template>
