<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ANNOUNCEMENT_CATEGORIES,
  addAnnouncement,
  announcements,
  announcementsError,
  announcementsLoaded,
  loadAnnouncements,
  removeAnnouncement,
  type Announcement,
} from '../announcements'
import { errorText } from '../api'
import { formatDate } from '../format'
import { matchesSearch } from '../search'
const props = defineProps<{ isAdmin: boolean; openModalOnMount?: boolean }>()

// Colour and icon of each category.
const CATEGORY_STYLE: Record<Announcement['category'], { tone: string; icon: string }> = {
  Rapport: { tone: 'blue', icon: '▤' },
  Viktigt: { tone: 'amber', icon: '△' },
  Driftinformation: { tone: 'purple', icon: '⚙' },
  Status: { tone: 'green', icon: '✓' },
}

// The "Rapporter" tab shows announcements in the category "Rapport"; "Alla" shows everything.
const FILTERS = [
  { label: 'Alla', category: '' },
  { label: 'Rapporter', category: 'Rapport' },
  { label: 'Viktigt', category: 'Viktigt' },
  { label: 'Driftinformation', category: 'Driftinformation' },
]
const searchQuery = ref('')
const selectedFilter = ref(FILTERS[0]!.label)

const visibleAnnouncements = computed(() => {
  const category = FILTERS.find((filter) => filter.label === selectedFilter.value)?.category
  return announcements.value.filter(
    (announcement) =>
      (!category || announcement.category === category) &&
      matchesSearch(
        [
          announcement.title,
          announcement.text,
          announcement.category,
          formatDate(announcement.created_at),
        ],
        searchQuery.value,
      ),
  )
})
const countLabel = computed(() => {
  const total = announcements.value.length
  const shown = visibleAnnouncements.value.length
  if (shown === total) return `${total} ${total === 1 ? 'meddelande' : 'meddelanden'}`
  return `${shown} av ${total} meddelanden`
})

// The server sends announcements newest first; the newest one is shown highlighted.
const isNewest = (announcement: Announcement) => announcement.id === announcements.value[0]?.id

const showModal = ref(false)
const submitting = ref(false)
const formError = ref('')
const actionError = ref('')
const emptyForm = () => ({ title: '', category: ANNOUNCEMENT_CATEGORIES[0], text: '' })
const form = reactive(emptyForm())

const openModal = () => {
  Object.assign(form, emptyForm())
  formError.value = ''
  showModal.value = true
}
const submitAnnouncement = async () => {
  submitting.value = true
  formError.value = ''
  try {
    await addAnnouncement({ ...form })
    showModal.value = false
  } catch (reason) {
    formError.value = errorText(reason, 'Kunde inte spara meddelandet.')
  } finally {
    submitting.value = false
  }
}
const deleteAnnouncement = async (announcement: Announcement) => {
  if (!window.confirm(`Ta bort meddelandet "${announcement.title}"?`)) return
  actionError.value = ''
  try {
    await removeAnnouncement(announcement.id)
  } catch (reason) {
    actionError.value = errorText(reason, 'Kunde inte ta bort meddelandet.')
  }
}

onMounted(() => {
  loadAnnouncements()
  if (props.isAdmin && props.openModalOnMount) openModal()
})
</script>

<template>
  <section class="reports-page">
    <div class="reports-intro">
      <div>
        <h1>Rapporter</h1>
        <p>Håll dig uppdaterad med nyheter och viktig information.</p>
      </div>
      <button v-if="isAdmin" type="button" @click="openModal">＋　Ny rapport</button>
    </div>
    <div class="reports-toolbar">
      <div class="search">
        <span aria-hidden="true">⌕</span>
        <input
          v-model="searchQuery"
          type="search"
          aria-label="Sök bland rapporter och meddelanden"
          placeholder="Sök bland rapporter och meddelanden"
        />
      </div>
      <nav aria-label="Kategori">
        <button
          v-for="filter in FILTERS"
          :key="filter.label"
          type="button"
          :aria-pressed="selectedFilter === filter.label"
          @click="selectedFilter = filter.label"
        >
          {{ filter.label }}
        </button>
      </nav>
    </div>
    <div class="reports-heading">
      <b>Senaste meddelanden</b><span>{{ countLabel }}</span>
    </div>
    <article
      v-for="announcement in visibleAnnouncements"
      :key="announcement.id"
      class="announcement"
      :class="{ featured: isNewest(announcement) }"
    >
      <i :class="CATEGORY_STYLE[announcement.category].tone">
        {{ CATEGORY_STYLE[announcement.category].icon }}
      </i>
      <div>
        <div class="announcement-top">
          <span class="tag" :class="CATEGORY_STYLE[announcement.category].tone">{{
            announcement.category
          }}</span>
          <span class="announcement-meta">
            <time>{{ formatDate(announcement.created_at) }}</time>
            <button
              v-if="isAdmin"
              type="button"
              class="announcement-delete"
              @click="deleteAnnouncement(announcement)"
            >
              Ta bort
            </button>
          </span>
        </div>
        <h2>{{ announcement.title }}</h2>
        <p>{{ announcement.text }}</p>
        <a>Läs mer　›</a>
      </div>
    </article>
    <p v-if="announcementsError" class="damage-error" role="alert">{{ announcementsError }}</p>
    <p v-if="actionError" class="damage-error" role="alert">{{ actionError }}</p>
    <p v-if="!announcements.length && announcementsLoaded" class="empty-message">
      Inga meddelanden ännu.
    </p>
    <p v-else-if="announcements.length && !visibleAnnouncements.length" class="empty-message">
      Inga meddelanden matchar din sökning.
    </p>
  </section>
  <div v-if="isAdmin && showModal" class="modal-backdrop" @click.self="showModal = false">
    <div
      class="material-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="announcement-modal-title"
    >
      <button class="modal-close" type="button" aria-label="Stäng" @click="showModal = false">
        ×
      </button>
      <div class="modal-icon">▤</div>
      <h2 id="announcement-modal-title">Ny rapport</h2>
      <p>Publicera information som alla användare kan läsa</p>
      <form @submit.prevent="submitAnnouncement">
        <label class="full"
          >Rubrik<input
            v-model="form.title"
            maxlength="120"
            required
            placeholder="Ex. Systemunderhåll planerat"
        /></label>
        <label class="full"
          >Kategori
          <select v-model="form.category" required>
            <option v-for="category in ANNOUNCEMENT_CATEGORIES" :key="category" :value="category">
              {{ category }}
            </option>
          </select></label
        >
        <label class="full"
          >Text
          <textarea
            v-model="form.text"
            maxlength="2000"
            rows="5"
            required
            placeholder="Skriv meddelandet här"
          ></textarea>
        </label>
        <p v-if="formError" class="damage-error full" role="alert">{{ formError }}</p>
        <div class="modal-actions">
          <button type="button" @click="showModal = false">Avbryt</button>
          <button type="submit" :disabled="submitting">Publicera</button>
        </div>
      </form>
    </div>
  </div>
</template>
