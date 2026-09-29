<script setup lang="ts">
import { announcements } from '../data/announcements'
const emit = defineEmits<{ 'create-report': [] }>()
defineProps<{ isAdmin: boolean }>()
</script>

<template>
  <section class="reports-page">
    <div class="reports-intro">
      <div>
        <h1>Rapporter</h1>
        <p>Håll dig uppdaterad med nyheter och viktig information.</p>
      </div>
      <button v-if="isAdmin" @click="emit('create-report')">＋　Ny rapport</button>
    </div>
    <div class="reports-toolbar">
      <div>⌕　 Sök bland rapporter och meddelanden</div>
      <nav><b>Alla</b><span>Rapporter</span><span>Viktigt</span><span>Driftinformation</span></nav>
    </div>
    <div class="reports-heading"><b>Senaste meddelanden</b><span>4 meddelanden</span></div>
    <article
      v-for="announcement in announcements"
      :key="announcement.title"
      class="announcement"
      :class="{ featured: announcement.featured }"
    >
      <i :class="announcement.tone">▤</i>
      <div>
        <div class="announcement-top">
          <span class="tag" :class="announcement.tone">{{ announcement.category }}</span>
          <time>{{ announcement.date }}</time>
        </div>
        <h2>{{ announcement.title }}</h2>
        <p>{{ announcement.text }}</p>
        <a>Läs mer　›</a>
      </div>
    </article>
  </section>
</template>
