<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { apiJson, apiRequest } from '../api'

defineProps<{ isAdmin: boolean }>()

type Member = {
  id: string
  name: string
  email: string
  role: 'Medlem' | 'Admin'
  last_login_at: string | null
  last_logout_at: string | null
  online: boolean
}
type Application = { id: string; name: string; email: string; submitted_at: string }

const activeTab = ref<'members' | 'applications'>('members')
const members = ref<Member[]>([])
const applications = ref<Application[]>([])
const error = ref('')
const formatDate = new Intl.DateTimeFormat('sv-SE', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})
const formatTime = new Intl.DateTimeFormat('sv-SE', { hour: '2-digit', minute: '2-digit' })
const formatTimestamp = (value: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return `${formatDate.format(date).replace('.', '')}, ${formatTime.format(date)}`
}
const load = async <T,>(target: Ref<T[]>, path: string, errorMessage: string) => {
  try {
    target.value = await apiJson<T[]>(path, { authenticated: true, errorMessage })
    error.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Kunde inte nå backend.'
  }
}
const loadMembers = () => load(members, '/members', 'Kunde inte hämta giltiga inloggningar.')
const loadApplications = () =>
  load(applications, '/account-applications', 'Kunde inte hämta ansökningar.')

const refresh = () => (activeTab.value === 'members' ? loadMembers() : loadApplications())

const validateApplication = async (id: string) => {
  try {
    await apiRequest(`/account-applications/${id}/validate`, {
      method: 'POST',
      authenticated: true,
    })
    await Promise.all([loadApplications(), loadMembers()])
  } catch {
    error.value = 'Kunde inte godkänna ansökan.'
  }
}

const rejectApplication = async (id: string) => {
  try {
    await apiRequest(`/account-applications/${id}`, { method: 'DELETE', authenticated: true })
    await loadApplications()
  } catch {
    error.value = 'Kunde inte avvisa ansökan.'
  }
}

const deleteMember = async (member: Member) => {
  if (!window.confirm(`Ta bort inloggningen för ${member.name} (${member.email})?`)) return
  try {
    await apiRequest(`/members/${member.id}`, { method: 'DELETE', authenticated: true })
    await loadMembers()
  } catch {
    error.value = 'Kunde inte ta bort inloggningen.'
  }
}

const updateRole = async (member: Member, role: 'Medlem' | 'Admin') => {
  const previousRole = member.role
  member.role = role
  try {
    await apiRequest(`/members/${member.id}/role`, {
      method: 'PATCH',
      authenticated: true,
      json: { role },
    })
    error.value = ''
  } catch {
    member.role = previousRole
    error.value = 'Kunde inte uppdatera rollen.'
  }
}

watch(activeTab, refresh)
// Keep the online status fresh while the members list is open.
let statusInterval: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  loadMembers()
  statusInterval = setInterval(() => {
    if (activeTab.value === 'members') loadMembers()
  }, 30 * 1000)
})
onUnmounted(() => clearInterval(statusInterval))
</script>

<template>
  <section class="account-page">
    <div class="account-intro">
      <div>
        <h1>Giltiga inloggningar</h1>
        <p>Konton i medlemsdatabasen som kan logga in.</p>
      </div>
    </div>

    <div class="account-tabs">
      <button :class="{ active: activeTab === 'members' }" @click="activeTab = 'members'">
        Giltiga inloggningar ({{ members.length }})
      </button>
      <button
        v-if="isAdmin"
        :class="{ active: activeTab === 'applications' }"
        @click="activeTab = 'applications'"
      >
        Ansökningar ({{ applications.length }})
      </button>
      <button class="refresh-button" @click="refresh">Uppdatera</button>
    </div>

    <p v-if="error" class="empty-applications">{{ error }}</p>

    <article v-if="activeTab === 'members'" class="user-table members-table">
      <header>
        <b>Giltiga inloggningar</b><span>{{ members.length }} konto(n)</span>
      </header>
      <div class="user-head">
        <span>ANVÄNDARE</span><span>ROLL</span><span>SENASTE INLOGGNING</span>
        <span>SENASTE UTLOGGNING</span><span>STATUS</span><span></span>
      </div>
      <div v-if="members.length === 0 && !error" class="empty-applications">
        Inga godkända konton ännu.
      </div>
      <div v-for="member in members" :key="member.id" class="user-row">
        <div class="person">
          <i>{{ member.name.slice(0, 2).toUpperCase() }}</i>
          <span
            ><b>{{ member.name }}</b
            ><small>{{ member.email }}</small></span
          >
        </div>
        <select
          class="role-select"
          :value="member.role"
          :aria-label="`Roll för ${member.name}`"
          @change="
            updateRole(member, ($event.target as HTMLSelectElement).value as 'Medlem' | 'Admin')
          "
        >
          <option value="Medlem">Medlem</option>
          <option value="Admin">Admin</option>
        </select>
        <span>{{ formatTimestamp(member.last_login_at) }}</span>
        <span>{{ formatTimestamp(member.last_logout_at) }}</span>
        <span
          ><strong :class="{ offline: !member.online }">{{
            member.online ? '● Online' : '● Offline'
          }}</strong></span
        >
        <button class="delete-member" @click="deleteMember(member)">Ta bort</button>
      </div>
    </article>

    <article v-else class="user-table">
      <header>
        <b>Ansökningar för validering</b><span>{{ applications.length }} väntar</span>
      </header>
      <div v-if="applications.length === 0 && !error" class="empty-applications">
        Inga väntande ansökningar.
      </div>
      <div v-for="application in applications" :key="application.id" class="user-row">
        <div class="person">
          <i>{{ application.name.slice(0, 2).toUpperCase() }}</i>
          <span
            ><b>{{ application.name }}</b
            ><small>{{ application.email }}</small></span
          >
        </div>
        <span>Ny ansökan</span><span>Medlem</span>
        <span><strong class="wait">● Väntar</strong></span>
        <span
          ><button @click="validateApplication(application.id)">Validera</button>
          <button class="reject" @click="rejectApplication(application.id)">Avvisa</button></span
        >
      </div>
    </article>
  </section>
</template>
