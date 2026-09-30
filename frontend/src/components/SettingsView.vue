<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  name: string
  email: string
  profileImage: string
  darkMode: boolean
}>()

const emit = defineEmits<{
  'save-profile': [profile: { name: string; image: string }]
  'update-theme': [enabled: boolean]
}>()

const displayName = ref(props.name)
const selectedImage = ref(props.profileImage)
const fileInput = ref<HTMLInputElement | null>(null)
const errorMessage = ref('')
const savedMessage = ref('')

const selectPhoto = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    errorMessage.value = 'Välj en bildfil.'
    return
  }
  if (file.size > 1.5 * 1024 * 1024) {
    errorMessage.value = 'Bilden måste vara mindre än 1,5 MB.'
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    selectedImage.value = String(reader.result ?? '')
    errorMessage.value = ''
    savedMessage.value = ''
  }
  reader.readAsDataURL(file)
}

const saveProfile = () => {
  const cleanName = displayName.value.trim()
  if (!cleanName) {
    errorMessage.value = 'Ange ett visningsnamn.'
    return
  }
  emit('save-profile', { name: cleanName, image: selectedImage.value })
  displayName.value = cleanName
  errorMessage.value = ''
  savedMessage.value = 'Profilen sparades på den här enheten.'
}

const updateTheme = (event: Event) => {
  emit('update-theme', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <section class="settings-page">
    <div class="settings-heading">
      <div>
        <h1>Inställningar</h1>
        <p>Profil och utseende</p>
      </div>
    </div>

    <div class="settings-content">
      <section class="settings-group" aria-labelledby="profile-heading">
        <div class="settings-group-heading">
          <h2 id="profile-heading">Profil</h2>
          <p>Uppgifterna visas i din arbetsyta.</p>
        </div>
        <form class="profile-form" @submit.prevent="saveProfile">
          <div class="profile-photo-row">
            <img v-if="selectedImage" class="settings-photo" :src="selectedImage" alt="Profilbild" />
            <div v-else class="settings-photo settings-photo-placeholder" aria-hidden="true">
              {{ displayName.slice(0, 2).toUpperCase() || '??' }}
            </div>
            <div class="photo-controls">
              <strong>Profilbild</strong>
              <div class="photo-actions">
                <button type="button" class="settings-secondary" @click="fileInput?.click()">Välj bild</button>
                <button v-if="selectedImage" type="button" class="settings-text-button" @click="selectedImage = ''; savedMessage = ''">Ta bort bild</button>
              </div>
              <small>Bildformat, högst 1,5 MB.</small>
              <input ref="fileInput" class="visually-hidden" type="file" accept="image/*" @change="selectPhoto" />
            </div>
          </div>

          <label class="settings-field">
            <span>Visningsnamn</span>
            <input v-model="displayName" type="text" maxlength="80" autocomplete="name" required />
          </label>
          <div class="settings-field">
            <span>E-postadress</span>
            <p>{{ props.email }}</p>
          </div>
          <p v-if="errorMessage" class="settings-message settings-error" role="alert">{{ errorMessage }}</p>
          <p v-else-if="savedMessage" class="settings-message" role="status">{{ savedMessage }}</p>
          <button class="settings-primary" type="submit">Spara profil</button>
        </form>
      </section>

      <section class="settings-group" aria-labelledby="appearance-heading">
        <div class="settings-group-heading">
          <h2 id="appearance-heading">Utseende</h2>
          <p>Välj hur arbetsytan ska visas.</p>
        </div>
        <label class="theme-setting">
          <span>
            <strong>Mörkt tema</strong>
            <small>Gäller hela webbplatsen och sparas på den här enheten.</small>
          </span>
          <input type="checkbox" :checked="props.darkMode" @change="updateTheme" />
        </label>
      </section>
    </div>
  </section>
</template>

<style scoped>
.settings-page {
  max-width: 900px;
  padding: 34px 40px;
  color: var(--settings-text);
}

.settings-heading {
  margin-bottom: 28px;
}

.settings-heading h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.settings-heading p,
.settings-group-heading p {
  margin: 0;
  color: var(--settings-muted);
  font-size: 12px;
}

.settings-content {
  border-top: 1px solid var(--settings-border);
}

.settings-group {
  display: grid;
  grid-template-columns: minmax(150px, 0.7fr) minmax(260px, 1.3fr);
  gap: 32px;
  padding: 26px 0;
  border-bottom: 1px solid var(--settings-border);
}

.settings-group-heading h2 {
  margin: 0 0 6px;
  font-size: 15px;
}

.profile-form {
  display: grid;
  gap: 18px;
}

.profile-photo-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.settings-photo {
  width: 76px;
  height: 76px;
  flex: none;
  border-radius: 50%;
  object-fit: cover;
}

.settings-photo-placeholder {
  display: grid;
  place-items: center;
  background: #e8edeb;
  color: #385249;
  font-size: 18px;
  font-weight: 700;
}

.photo-controls {
  display: grid;
  justify-items: start;
  gap: 7px;
}

.photo-controls strong,
.theme-setting strong {
  font-size: 12px;
}

.photo-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.photo-controls small,
.theme-setting small {
  color: var(--settings-muted);
  font-size: 11px;
}

.settings-field {
  display: grid;
  gap: 7px;
  color: var(--settings-text);
  font-size: 11px;
}

.settings-field input {
  width: 100%;
  height: 40px;
  padding: 0 11px;
  border: 1px solid var(--settings-border);
  border-radius: 6px;
  background: var(--settings-field);
  color: var(--settings-text);
  font: inherit;
}

.settings-field p {
  margin: 0;
  color: var(--settings-muted);
}

.settings-secondary,
.settings-primary {
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid var(--settings-border);
  border-radius: 6px;
  background: var(--settings-surface);
  color: var(--settings-text);
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}

.settings-primary {
  justify-self: start;
  border-color: #263d37;
  background: #263d37;
  color: #fff;
  font-weight: 600;
}

.settings-text-button {
  border: 0;
  background: none;
  color: var(--settings-muted);
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}

.settings-message {
  margin: -6px 0 0;
  color: #337b5b;
  font-size: 11px;
}

.settings-error {
  color: #bd4949;
}

.theme-setting {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.theme-setting span {
  display: grid;
  gap: 5px;
}

.theme-setting input {
  width: 42px;
  height: 24px;
  flex: none;
  appearance: none;
  border: 1px solid #98a29e;
  border-radius: 99px;
  background: #d9dfdc;
  cursor: pointer;
  transition: background-color 0.18s ease;
}

.theme-setting input::before {
  display: block;
  width: 18px;
  height: 18px;
  margin: 2px;
  border-radius: 50%;
  background: #fff;
  content: '';
  transition: transform 0.18s ease;
}

.theme-setting input:checked {
  border-color: #53796c;
  background: #53796c;
}

.theme-setting input:checked::before {
  transform: translateX(18px);
}

.theme-setting input:focus-visible,
.settings-secondary:focus-visible,
.settings-primary:focus-visible,
.settings-text-button:focus-visible {
  outline: 2px solid #53796c;
  outline-offset: 2px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  clip-path: inset(50%);
}

@media (max-width: 700px) {
  .settings-page {
    padding: 28px 20px;
  }

  .settings-group {
    grid-template-columns: 1fr;
    gap: 18px;
  }
}
</style>