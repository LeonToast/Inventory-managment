<script setup lang="ts">
import { computed, defineAsyncComponent, ref, onMounted, onUnmounted } from 'vue'
import LandingView from './components/LandingView.vue'
import OverviewView from './components/OverviewView.vue'
import { ACCOUNT_STORAGE_KEY, apiRequest, storedAccount, type Account } from './api'
import { clearDamageReports } from './damageReports'
import { useHeartbeat } from './useHeartbeat'
import { useIdleTimeout } from './useIdleTimeout'

defineOptions({ name: 'MainApp' })

// Secondary pages are split into their own chunks and only downloaded when first opened.
const MaterialView = defineAsyncComponent(() => import('./components/MaterialView.vue'))
const DeliveryView = defineAsyncComponent(() => import('./components/DeliveryView.vue'))
const AccountView = defineAsyncComponent(() => import('./components/AccountView.vue'))
const ReportsView = defineAsyncComponent(() => import('./components/ReportsView.vue'))
const CreateReportView = defineAsyncComponent(() => import('./components/CreateReportView.vue'))

// --- Account and page state -------------------------------------------------------------------

const currentAccount = ref<Account | null>(storedAccount())
const showLanding = ref(!currentAccount.value)
const logoutNotice = ref('')
const active = ref('Hem')
const showReportForm = ref(false)
const openDamageOnMount = ref(false)

const isAdmin = computed(() => currentAccount.value?.role === 'Admin')
const accountInitials = computed(
  () => currentAccount.value?.name.trim().slice(0, 2).toUpperCase() || '',
)

const handleLogin = (account: Account) => {
  logoutNotice.value = ''
  currentAccount.value = account
  showLanding.value = false
}

const logout = () => {
  // Record the logout time on the server. This starts before the token is cleared, and a failed
  // request never blocks logging out.
  if (currentAccount.value)
    apiRequest('/logout', { method: 'POST', authenticated: true }).catch(() => {})
  localStorage.removeItem(ACCOUNT_STORAGE_KEY)
  clearDamageReports()
  currentAccount.value = null
  showAccountMenu.value = false
  showReportForm.value = false
  active.value = 'Hem'
  showLanding.value = true
}

// --- Session: inactivity warning, automatic logout and heartbeat ------------------------------

const { showWarning, secondsLeft, dismissWarning } = useIdleTimeout(
  () => currentAccount.value !== null,
  () => {
    logout()
    logoutNotice.value = 'Du har loggats ut på grund av inaktivitet.'
  },
)
useHeartbeat(
  () => currentAccount.value !== null,
  () => showWarning.value,
)

const countdown = computed(
  () => `${Math.floor(secondsLeft.value / 60)}:${String(secondsLeft.value % 60).padStart(2, '0')}`,
)

// --- Navigation -------------------------------------------------------------------------------

const navigation = computed(() => [
  { label: 'Hem', icon: '⌂' },
  { label: 'Materiel', icon: '◇' },
  { label: 'Leverans', icon: '⌾' },
  ...(isAdmin.value ? [{ label: 'Hantera konton', icon: '♧' }] : []),
  { label: 'Rapporter', icon: '▥' },
  { label: 'Inställningar', icon: '⚙' },
])

const selectPage = (page: string) => {
  active.value = page
  showReportForm.value = false
  openDamageOnMount.value = false
}

const reportDamagedItem = () => {
  openDamageOnMount.value = true
  active.value = 'Materiel'
  showReportForm.value = false
}

// --- Header clock and account menu ------------------------------------------------------------

const timeFormat = new Intl.DateTimeFormat('sv-SE', { timeStyle: 'medium' })
const currentTime = ref(timeFormat.format())
const showAccountMenu = ref(false)
const accountMenuContainer = ref<HTMLElement | null>(null)

const closeAccountMenuOutside = (event: PointerEvent) => {
  if (!accountMenuContainer.value?.contains(event.target as Node)) showAccountMenu.value = false
}
const closeAccountMenuOnEscape = (event: KeyboardEvent) => {
  if (event.key === 'Escape') showAccountMenu.value = false
}

let clockInterval: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  clockInterval = setInterval(() => {
    currentTime.value = timeFormat.format()
  }, 1000)
  document.addEventListener('pointerdown', closeAccountMenuOutside)
  document.addEventListener('keydown', closeAccountMenuOnEscape)
})
onUnmounted(() => {
  clearInterval(clockInterval)
  document.removeEventListener('pointerdown', closeAccountMenuOutside)
  document.removeEventListener('keydown', closeAccountMenuOnEscape)
})
</script>

<template>
  <LandingView v-if="showLanding" :notice="logoutNotice" @login="handleLogin" />
  <div v-else class="app">
    <aside>
      <div class="brand"><b>⬡</b><strong>Smart lagring</strong></div>
      <div class="menu">
        <small>MENY</small>
        <button
          v-for="item in navigation"
          :key="item.label"
          :class="{ on: active === item.label }"
          @click="selectPage(item.label)"
        >
          <i>{{ item.icon }}</i
          >{{ item.label }}<em v-if="item.label === 'Materiel'">1,284</em>
        </button>
      </div>
      <div ref="accountMenuContainer" class="user-area">
        <button
          class="user"
          type="button"
          aria-haspopup="menu"
          :aria-expanded="showAccountMenu"
          aria-controls="account-menu"
          @click="showAccountMenu = !showAccountMenu"
        >
          <span>{{ accountInitials }}</span>
          <b
            >{{ currentAccount?.name }}<small>{{ currentAccount?.role }}</small></b
          >
          <span class="user-chevron" aria-hidden="true">›</span>
        </button>
        <div v-if="showAccountMenu" id="account-menu" class="user-menu" role="menu">
          <button type="button" role="menuitem" @click="logout">Logga ut</button>
        </div>
      </div>
    </aside>
    <main>
      <header>
        <span class="crumb">Smart lagring　›　<strong>Översikt</strong></span>
        <div>
          ◷　{{ currentTime }}　　♧　 <span class="avatar">{{ accountInitials }}</span
          >　<b>{{ currentAccount?.role }}⌄</b>
        </div>
      </header>
      <CreateReportView v-if="showReportForm && isAdmin" @back="showReportForm = false" />
      <DeliveryView v-else-if="active === 'Leverans'" :is-admin="isAdmin" />
      <MaterialView
        v-else-if="active === 'Materiel'"
        :is-admin="isAdmin"
        :open-damage-on-mount="openDamageOnMount"
      />
      <AccountView v-else-if="active === 'Hantera konton' && isAdmin" :is-admin="isAdmin" />
      <ReportsView
        v-else-if="active === 'Rapporter'"
        :is-admin="isAdmin"
        @create-report="showReportForm = true"
      />

      <OverviewView
        v-else
        :account-name="currentAccount?.name || ''"
        :is-admin="isAdmin"
        @create-report="showReportForm = true"
        @report-damaged-item="reportDamagedItem"
      />
    </main>
    <button class="help">?</button>
    <div v-if="showWarning" class="modal-backdrop idle-modal">
      <div
        class="material-modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="idle-modal-title"
      >
        <div class="modal-icon">◷</div>
        <h2 id="idle-modal-title">Är du kvar?</h2>
        <p>
          Du har inte varit aktiv på sidan och loggas snart ut. Du loggas ut om
          <strong>{{ countdown }}</strong
          >.
        </p>
        <div class="modal-actions">
          <button
            type="button"
            :ref="(el) => (el as HTMLElement | null)?.focus()"
            @click="dismissWarning"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
