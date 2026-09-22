<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

defineProps<{ isAdmin: boolean }>()

type Member = { id: string; name: string; email: string; role: 'Medlem' | 'Admin' }
type Application = { id: string; name: string; email: string; submitted_at: string }

const activeTab = ref<'members' | 'applications'>('members')
const members = ref<Member[]>([])
const applications = ref<Application[]>([])
const error = ref('')
const savedAccount = JSON.parse(localStorage.getItem('smart-lagring-account') || 'null') as { role?: string; access_token?: string } | null
const adminHeaders = () => ({ Authorization: `Bearer ${savedAccount?.access_token || ''}` })

const loadMembers = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8001/members')
    if (!response.ok) throw new Error('Kunde inte hämta giltiga inloggningar.')
    members.value = await response.json()
    error.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Kunde inte nå backend.'
  }
}

const loadApplications = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8001/account-applications', { headers: adminHeaders() })
    if (!response.ok) throw new Error('Kunde inte hämta ansökningar.')
    applications.value = await response.json()
    error.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Kunde inte nå backend.'
  }
}

const refresh = () => activeTab.value === 'members' ? loadMembers() : loadApplications()

const validateApplication = async (id: string) => {
  const response = await fetch(`http://127.0.0.1:8001/account-applications/${id}/validate`, { method: 'POST', headers: adminHeaders() })
  if (response.ok) await Promise.all([loadApplications(), loadMembers()])
  else error.value = 'Kunde inte godkänna ansökan.'
}

const rejectApplication = async (id: string) => {
  const response = await fetch(`http://127.0.0.1:8001/account-applications/${id}/reject`, { method: 'POST', headers: adminHeaders() })
  if (response.ok) await loadApplications()
  else error.value = 'Kunde inte avvisa ansökan.'
}

const deleteMember = async (member: Member) => {
  if (!window.confirm(`Ta bort inloggningen för ${member.name} (${member.email})?`)) return
  const response = await fetch(`http://127.0.0.1:8001/members/${member.id}`, { method: 'DELETE', headers: adminHeaders() })
  if (response.ok) await loadMembers()
  else error.value = 'Kunde inte ta bort inloggningen.'
}

const updateRole = async (member: Member, role: 'Medlem' | 'Admin') => {
  const previousRole = member.role
  member.role = role
  const response = await fetch(`http://127.0.0.1:8001/members/${member.id}/role`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...adminHeaders() },
    body: JSON.stringify({ role }),
  })
  if (!response.ok) {
    member.role = previousRole
    error.value = 'Kunde inte uppdatera rollen.'
  } else {
    error.value = ''
  }
}

watch(activeTab, refresh)
onMounted(loadMembers)
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
      <button v-if="isAdmin" :class="{ active: activeTab === 'applications' }" @click="activeTab = 'applications'">
        Ansökningar ({{ applications.length }})
      </button>
      <button class="refresh-button" @click="refresh">Uppdatera</button>
    </div>

    <p v-if="error" class="empty-applications">{{ error }}</p>

    <article v-if="activeTab === 'members'" class="user-table">
      <header><b>Giltiga inloggningar</b><span>{{ members.length }} konto(n)</span></header>
      <div class="user-head"><span>ANVÄNDARE</span><span>ROLL</span><span>OMFATTNING</span><span>STATUS</span><span></span></div>
      <div v-if="members.length === 0 && !error" class="empty-applications">Inga godkända konton ännu.</div>
      <div v-for="member in members" :key="member.id" class="user-row">
        <div class="person">
          <i>{{ member.name.slice(0, 2).toUpperCase() }}</i>
          <span><b>{{ member.name }}</b><small>{{ member.email }}</small></span>
        </div>
        <select class="role-select" :value="member.role" :aria-label="`Roll för ${member.name}`" @change="updateRole(member, ($event.target as HTMLSelectElement).value as 'Medlem' | 'Admin')">
          <option value="Medlem">Medlem</option>
          <option value="Admin">Admin</option>
        </select>
        <span>—</span><span><strong>● Aktiv</strong></span>
        <button class="delete-member" @click="deleteMember(member)">Ta bort</button>
      </div>
    </article>

    <article v-else class="user-table">
      <header><b>Ansökningar för validering</b><span>{{ applications.length }} väntar</span></header>
      <div v-if="applications.length === 0 && !error" class="empty-applications">Inga väntande ansökningar.</div>
      <div v-for="application in applications" :key="application.id" class="user-row">
        <div class="person">
          <i>{{ application.name.slice(0, 2).toUpperCase() }}</i>
          <span><b>{{ application.name }}</b><small>{{ application.email }}</small></span>
        </div>
        <span>Ny ansökan</span><span>Medlem</span><span><strong class="wait">● Väntar</strong></span>
        <span><button @click="validateApplication(application.id)">Validera</button><button class="reject" @click="rejectApplication(application.id)">Avvisa</button></span>
      </div>
    </article>
  </section>
</template>
