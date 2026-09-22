<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
const emit = defineEmits<{ login: [account?: { name: string; email: string; role: string; access_token: string }] }>()
const showSignupForm = ref(false)
const showPendingMessage = ref(false)
const showLoginForm = ref(false)
const loginForm = reactive({ email: '', password: '' })
const loginError = ref('')
const submitLogin = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8001/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: loginForm.email.trim(), password: loginForm.password }),
    })
    if (!response.ok) {
      const result = await response.json().catch(() => null)
      throw new Error(result?.detail || `Login failed (${response.status}).`)
    }
    const account = await response.json()
    localStorage.setItem('smart-lagring-account', JSON.stringify(account))
    loginError.value = ''
    showLoginForm.value = false
    emit('login', account)
  } catch (error) {
    loginError.value = error instanceof TypeError
      ? 'Kan inte nå backend. Kontrollera att Uvicorn körs på port 8001.'
      : error instanceof Error
        ? error.message
        : 'Inloggningen misslyckades.'
  }
}
const signupForm = reactive({ name: '', email: '', password: '', confirmPassword: '' })
const canRegister = computed(() => signupForm.name.trim() && /^[^\s@]+@[^\s@]+$/.test(signupForm.email.trim()) && signupForm.password.length >= 8 && signupForm.confirmPassword && signupForm.password === signupForm.confirmPassword)
const showSignupErrors = ref(false)
const submitSignup = async () => {
  showSignupErrors.value = true
  if (canRegister.value) {
    const response = await fetch('http://127.0.0.1:8001/account-applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: signupForm.name.trim(), email: signupForm.email.trim(), password: signupForm.password }) })
    if (!response.ok) return
    showSignupForm.value = false
    showPendingMessage.value = true
  }
}
</script>

<template>
  <div class="landing-page">
    <header class="landing-nav">
      <div class="landing-brand"><span aria-hidden="true">▦</span><b>Smart Lagring</b></div>
      <nav aria-label="Huvudmeny">
        <a href="#home">Hem</a><a href="#landing-features">Materiel</a><a href="#landing-features">Platser</a><a href="#landing-features">Rapporter</a>
      </nav>
    </header>
    <main id="home" class="landing-main">
      <div class="landing-icon" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <rect x="5" y="5" width="21" height="20" />
          <path d="M7 10h17M7 15h17M7 20h17" />
          <path class="landing-icon-small" d="M22 27h7v-5h-7zM23 24h5" />
        </svg>
      </div>
      <div class="landing-eyebrow">—　 INVENTORY MANAGEMENT　 —</div>
      <h1>Smart Lagring</h1><div class="landing-rule"></div>
      <p>Streamline your warehouse operations with real-time inventory tracking, automated stock alerts, multi-location management, and detailed reporting — all in one powerful platform built for modern businesses.</p>
      <div class="landing-actions"><button @click="showLoginForm = true">Logga in</button><button class="secondary" @click="showSignupForm = true">Formulär</button></div>
      <section id="landing-features" class="landing-features"><h2>Allt du behöver för smartare lager</h2><p>Få full kontroll över material, leveranser, konton och rapporter på en och samma plats.</p></section>
    </main>
    <div v-if="showSignupForm" class="signup-backdrop" @click.self="showSignupForm = false"><div class="signup-card"><button class="signup-close" @click="showSignupForm = false">×</button><div class="signup-icon">▤</div><h2>Smart Lagring</h2><small>WAREHOUSE MANAGEMENT SYSTEM</small><p>Skapa konto</p><form @submit.prevent="submitSignup"><label>Namn<input v-model="signupForm.name" placeholder="Förnamn Efternamn" /></label><label>E-postadress<input type="email" :class="{ invalid: showSignupErrors && !/^[^\s@]+@[^\s@]+$/.test(signupForm.email.trim()) }" v-model="signupForm.email" placeholder="namn@foretag.se" /></label><label>Lösenord<input :class="{ invalid: showSignupErrors && signupForm.password.length < 8 }" v-model="signupForm.password" type="password" placeholder="••••••••" /></label><label>Bekräfta lösenord<input :class="{ invalid: showSignupErrors && (!signupForm.confirmPassword || signupForm.password !== signupForm.confirmPassword) }" v-model="signupForm.confirmPassword" type="password" placeholder="••••••••" /></label><div v-if="showSignupErrors && !canRegister" class="signup-errors">Fyll i alla fält, använd minst 8 tecken i lösenordet, ange en giltig e-postadress och se till att lösenorden matchar.</div><button type="submit">Registrera konto →</button></form><footer>Har du redan ett konto? <b @click="$emit('login'); showSignupForm = false">Logga in</b><small>© Smart Lagring. Alla rättigheter förbehålls.</small></footer></div></div>
    <div v-if="showLoginForm" class="login-backdrop" @click.self="showLoginForm = false"><div class="login-card"><button class="signup-close" @click="showLoginForm = false">×</button><div class="signup-icon">▤</div><h2>Smart Lagring</h2><small>WAREHOUSE MANAGEMENT SYSTEM</small><p>Inloggning</p><form @submit.prevent="submitLogin"><label>E-postadress<input v-model="loginForm.email" type="email" placeholder="namn@foretag.se" required /></label><label>Lösenord<input v-model="loginForm.password" type="password" placeholder="••••••••" required /></label><a>Glömt lösenord?</a><p v-if="loginError" class="login-error">{{ loginError }}</p><button type="submit">Logga in →</button></form><footer>© 2026 Smart Lagring. Alla rättigheter förbehålls.</footer></div></div>
    <div v-if="showPendingMessage" class="pending-backdrop" @click.self="showPendingMessage = false"><div class="pending-card"><div class="pending-icon">✓</div><h2>Registrering mottagen</h2><p>Din registrering väntar på validering.</p><button @click="showPendingMessage = false">Stäng</button></div></div>
  </div>
</template>
