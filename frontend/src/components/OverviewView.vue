<script setup lang="ts">
import { onMounted } from 'vue'
import { damageReportsLoaded, damagedCount, loadDamageReports } from '../damageReports'
import { activities, overviewStatistics, warehouseCapacities } from '../data/overview'

const { accountName, isAdmin } = defineProps<{ accountName: string; isAdmin: boolean }>()
const emit = defineEmits<{ createReport: []; reportDamagedItem: [] }>()
onMounted(loadDamageReports)
</script>

<template>
  <section>
    <div class="intro">
      <div>
        <h1>Översikt</h1>
        <p>Välkommen tillbaka, {{ accountName }}. Här är dagens sammanfattning.</p>
      </div>
      <span>●　Alla system fungerar</span>
    </div>
    <div class="stats">
      <article v-for="statistic in overviewStatistics" :key="statistic.label">
        <small>{{ statistic.label }}</small
        ><b>{{
          statistic.label === 'SKADAT' && damageReportsLoaded ? damagedCount : statistic.value
        }}</b>
        <span>{{ statistic.unit }}</span
        ><em v-if="statistic.change">{{ statistic.change }}</em>
      </article>
    </div>
    <div class="grid">
      <div>
        <article class="card activity">
          <div class="title"><b>Senaste aktivitet</b><a>Visa alla ↗</a></div>
          <div class="row" v-for="activity in activities" :key="activity.title">
            <i :class="activity.color">{{ activity.icon }}</i>
            <div>
              <b>{{ activity.title }}</b
              ><small>{{ activity.description }}</small>
            </div>
            <time>{{ activity.time }}</time>
          </div>
        </article>
        <article class="card overview">
          <div class="title">
            <div><b>Lageröversikt</b><small>Aktuell fördelning mellan dina lager.</small></div>
            <a>Visa rapport ›</a>
          </div>
          <div class="dist"><i /><i /><i /></div>
          <p>
            ● Lager A　43%　　　　　　　　　<span
              >● Lager B　31%　　　　　　　　　● Lager C　26%</span
            >
          </p>
        </article>
      </div>
      <div class="right">
        <article class="quick">
          <b>Snabbåtgärder</b>
          <button type="button" @click="emit('reportDamagedItem')">
            △　Rapportera skadad vara
          </button>
          <button v-if="isAdmin" type="button" @click="emit('createReport')">
            ＋　Skapa rapport
          </button>
        </article>
        <article class="card capacity">
          <b>Lagerkapacitet</b><small>Totalt</small>
          <div v-for="capacity in warehouseCapacities" :key="capacity.name">
            {{ capacity.name }} <span>{{ capacity.percentage }}</span
            ><i><b :class="capacity.color" :style="{ width: capacity.percentage }" /></i>
          </div>
          <a>Se full rapport　›</a>
        </article>
      </div>
    </div>
  </section>
</template>
