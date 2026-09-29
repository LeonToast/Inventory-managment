<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  activities,
  activityError,
  activityLoaded,
  loadActivity,
  timeAgo,
  type ActivityKind,
} from '../activity'
import { damageReportsLoaded, damagedCount, loadDamageReports } from '../damageReports'
import { overviewStatistics, warehouseCapacities } from '../data/overview'
import { loadMaterials, materials, materialsLoaded } from '../materials'

const { accountName, isAdmin } = defineProps<{ accountName: string; isAdmin: boolean }>()
const emit = defineEmits<{ createReport: []; reportDamagedItem: [] }>()

// TOTALT LAGER is the sum of the quantity of every saved material (units are not converted).
const totalUnits = computed(() =>
  materials.value.reduce((sum, material) => sum + material.quantity, 0).toLocaleString('sv-SE'),
)
const statisticValue = (statistic: (typeof overviewStatistics)[number]) => {
  if (statistic.label === 'SKADAT' && damageReportsLoaded.value) return damagedCount.value
  if (statistic.label === 'TOTALT LAGER' && materialsLoaded.value) return totalUnits.value
  return statistic.value
}

// Colour and icon of each kind of event in "Senaste aktivitet".
const ACTIVITY_STYLE: Record<ActivityKind, { color: string; icon: string }> = {
  damage: { color: 'amber', icon: '△' },
  report: { color: 'purple', icon: '▤' },
  material: { color: 'blue', icon: '◇' },
}

// "2 min sedan" is measured against this clock, which is refreshed while the page is open.
const now = ref(Date.now())
let clock: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  loadDamageReports()
  loadMaterials()
  loadActivity()
  clock = setInterval(() => {
    now.value = Date.now()
  }, 30_000)
})
onUnmounted(() => clearInterval(clock))
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
        <small>{{ statistic.label }}</small>
        <b>{{ statisticValue(statistic) }}</b>
        <span>{{ statistic.unit }}</span>
        <em v-if="statistic.change">{{ statistic.change }}</em>
      </article>
    </div>
    <div class="grid">
      <div>
        <article class="card activity">
          <div class="title"><b>Senaste aktivitet</b></div>
          <div class="row" v-for="activity in activities" :key="activity.id">
            <i :class="ACTIVITY_STYLE[activity.kind].color">{{
              ACTIVITY_STYLE[activity.kind].icon
            }}</i>
            <div>
              <b>{{ activity.title }}</b>
              <small>{{ activity.description }}</small>
            </div>
            <time :datetime="activity.created_at">{{ timeAgo(activity.created_at, now) }}</time>
          </div>
          <p v-if="activityError" class="activity-empty error" role="alert">{{ activityError }}</p>
          <p v-else-if="!activities.length && activityLoaded" class="activity-empty">
            Ingen aktivitet ännu.
          </p>
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
          <button v-if="isAdmin" type="button" @click="emit('createReport')">＋　Ny rapport</button>
        </article>
        <article class="card capacity">
          <b>Lagerkapacitet</b><small>Totalt</small>
          <div v-for="capacity in warehouseCapacities" :key="capacity.name">
            {{ capacity.name }} <span>{{ capacity.percentage }}</span>
            <i><b :class="capacity.color" :style="{ width: capacity.percentage }" /></i>
          </div>
          <a>Se full rapport　›</a>
        </article>
      </div>
    </div>
  </section>
</template>
