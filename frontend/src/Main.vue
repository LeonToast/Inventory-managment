<script setup lang="ts">
import { computed, ref, provide } from 'vue'
import MaterialView from './components/MaterialView.vue'
import DeliveryView from './components/DeliveryView.vue'
import AccountView from './components/AccountView.vue'
import ReportsView from './components/ReportsView.vue'
import CreateReportView from './components/CreateReportView.vue'
import LandingView from './components/LandingView.vue'
const showLanding = ref(true)
const showReportForm = ref(false)
const currentAccount = ref<{ name: string; email: string; role: string; access_token: string } | null>(null)
const isAdmin = computed(() => currentAccount.value?.role === 'Admin')
const handleLogin = (account?: { name: string; email: string; role: string; access_token: string }) => {
  currentAccount.value = account ?? { name: 'Medlem', email: '', role: 'Medlem', access_token: '' }
  showLanding.value = false
}
const pendingAccounts = ref<Array<{ name: string; email: string; submittedAt: string }>>([])
provide('pendingAccounts', pendingAccounts)
const active = ref('Hem')
const nav = computed(() => ['Hem', 'Materiel', 'Leverans', ...(isAdmin.value ? ['Hantera konton'] : []), 'Rapporter', 'Inställningar'])
const activities = [{ title: 'Ny leverans registrerad', description: 'Lager A · Sektion 3', time: '2 min sedan', color: 'blue', icon: '◇' }, { title: 'Lågt lagersaldo', description: 'Produkt #4821 · Lager B', time: '18 min sedan', color: 'amber', icon: '△' }, { title: 'Inventering slutförd', description: 'Lager C · Alla sektioner', time: '1 tim sedan', color: 'green', icon: '✓' }, { title: 'Rapport genererad', description: 'Månadsrapport · Oktober', time: '3 tim sedan', color: 'purple', icon: '▤' }]
const overviewStatistics = [{ label: 'TOTALT LAGER', value: '1,284', unit: 'enheter', change: '+12' }, { label: 'LEVERERAS', value: '47', unit: 'enheter', change: '+3' }, { label: 'SKADAT', value: '8', unit: 'varningar', change: '-2' }]
const warehouseCapacities = [{ name: 'Lager A', percentage: '78%', color: 'black' }, { name: 'Lager B', percentage: '61%', color: 'blue' }, { name: 'Lager C', percentage: '43%', color: 'green' }]
</script>
<template>
<LandingView v-if="showLanding" @login="handleLogin" />
<div v-else class="app">
    <aside>
      <div class="brand"><b>⬡</b><strong>Smart lagring</strong></div>
      <div class="menu"><small>MENY</small><button v-for="navigationItem in nav" :key="navigationItem" :class="{ on: active === navigationItem }"
          @click="active = navigationItem; showReportForm = false"><i>{{ ['⌂', '◇', '⌾', '♧', '▥', '⚙'][nav.indexOf(navigationItem)] }}</i>{{ navigationItem }}<em
            v-if="navigationItem === 'Materiel'">1,284</em></button></div>
      <div class="user"><span>{{ currentAccount?.name.slice(0, 2).toUpperCase() }}</span><b>{{ currentAccount?.name }}<small>{{ currentAccount?.role }}</small></b>›</div>
    </aside>
    <main>
      <header><span class="crumb">Smart lagring　›　<strong>Översikt</strong></span>
        <div>◷　10:57:17　　♧　 <span class="avatar">AD</span>　<b>Admin⌄</b></div>
      </header>
      <CreateReportView v-if="showReportForm && isAdmin" @back="showReportForm = false" />
      <DeliveryView v-else-if="active === 'Leverans'" :is-admin="isAdmin" />
      <MaterialView v-else-if="active === 'Materiel'" :is-admin="isAdmin" />
      <AccountView v-else-if="active === 'Hantera konton' && isAdmin" :is-admin="isAdmin" />
      <ReportsView v-else-if="active === 'Rapporter'" :is-admin="isAdmin" @create-report="showReportForm = true" />


      <section v-else>
        <div class="intro">
          <div>
            <h1>Översikt</h1>
            <p>Välkommen tillbaka, Admin. Här är dagens sammanfattning.</p>
          </div><span>●　Alla system fungerar</span>
        </div>
        <div class="stats">
          <article
            v-for="statistic in overviewStatistics"
            :key="statistic.label"><small>{{ statistic.label }}</small><b>{{ statistic.value }}</b> <span>{{ statistic.unit }}</span><em>{{ statistic.change }}</em></article>
        </div>
        <div class="grid">
          <div>
            <article class="card activity">
              <div class="title"><b>Senaste aktivitet</b><a>Visa alla ↗</a></div>
              <div class="row" v-for="activity in activities" :key="activity.title"><i :class="activity.color">{{ activity.icon }}</i>
                <div><b>{{ activity.title }}</b><small>{{ activity.description }}</small></div><time>{{ activity.time }}</time>
              </div>
            </article>
            <article class="card overview">
              <div class="title">
                <div><b>Lageröversikt</b><small>Aktuell fördelning mellan dina lager.</small></div><a>Visa rapport ›</a>
              </div>
              <div class="dist"><i /><i /><i /></div>
              <p>● Lager A　43%　　　　　　　　　<span>● Lager B　31%　　　　　　　　　● Lager C　26%</span></p>
            </article>
          </div>
          <div class="right">
            <article class="quick"><b>Snabbåtgärder</b><button v-if="isAdmin" @click="showReportForm = true">＋　Skapa rapport</button></article>
            <article class="card capacity"><b>Lagerkapacitet</b><small>Totalt</small>
              <div v-for="capacity in warehouseCapacities" :key="capacity.name">{{ capacity.name }} <span>{{ capacity.percentage }}</span><i><b :class="capacity.color" :style="{ width: capacity.percentage }" /></i></div>
              <a>Se
                full rapport　›</a>
            </article>
          </div>
        </div>
      </section>
    </main><button class="help">?</button>
  </div>
</template>
