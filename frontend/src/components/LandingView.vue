<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import QRCode from 'qrcode'
const emit = defineEmits<{ login: [account?: { name: string; email: string; role: string; access_token: string }] }>()
const showSignupForm = ref(false)
const showPendingMessage = ref(false)
const showLoginForm = ref(false)
const loginForm = reactive({ email: '', password: '' })
const loginError = ref('')
const loginRequiresTwoFactor = ref(false)
const loginTwoFactorCode = ref('')
const apiErrorMessage = (result: unknown, fallback: string) => {
  if (!result || typeof result !== 'object' || !('detail' in result)) return fallback
  const detail = result.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(item => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object' && 'msg' in item) return String(item.msg)
      return ''
    }).filter(Boolean)
    if (messages.length) return messages.join(' ')
  }
  return fallback
}
const isValidEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)
const submitLogin = async () => {
  try {
    const response = await fetch('http://localhost:8000/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: loginForm.email.trim(),
        password: loginForm.password,
        ...(loginRequiresTwoFactor.value ? { two_factor_code: loginTwoFactorCode.value } : {}),
      }),
    })
    const account = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(apiErrorMessage(account, `Login failed (${response.status}).`))
    }
    if (account?.requires_two_factor) {
      loginRequiresTwoFactor.value = true
      loginError.value = ''
      return
    }
    localStorage.setItem('smart-lagring-account', JSON.stringify(account))
    loginError.value = ''
    loginRequiresTwoFactor.value = false
    loginTwoFactorCode.value = ''
    showLoginForm.value = false
    emit('login', account)
  } catch (error) {
    loginError.value = error instanceof TypeError
      ? 'Kan inte nå backend. Kontrollera att Uvicorn körs på port 8000.'
      : error instanceof Error
        ? error.message
        : 'Inloggningen misslyckades.'
  }
}
const signupForm = reactive({ name: '', email: '', password: '', confirmPassword: '' })
const twoFactorEnabled = ref(false)
const twoFactorCode = ref('')
const twoFactorSetup = ref<{ secret: string; otpauth_uri: string; email: string } | null>(null)
const twoFactorQrCode = ref('')
const twoFactorSetupError = ref('')
const twoFactorSetupLoading = ref(false)
const signupError = ref('')
const normalizedSignupEmail = computed(() => signupForm.email.trim().toLowerCase())
const canRegister = computed(() => Boolean(
  signupForm.name.trim()
  && isValidEmail(normalizedSignupEmail.value)
  && signupForm.password.length >= 8
  && signupForm.confirmPassword
  && signupForm.password === signupForm.confirmPassword
  && (!twoFactorEnabled.value || (
    twoFactorSetup.value?.email === normalizedSignupEmail.value
    && /^\d{6}$/.test(twoFactorCode.value)
  )),
))
const showSignupErrors = ref(false)
watch(normalizedSignupEmail, email => {
  if (twoFactorSetup.value && twoFactorSetup.value.email !== email) {
    twoFactorSetup.value = null
    twoFactorQrCode.value = ''
    twoFactorCode.value = ''
    twoFactorSetupError.value = 'E-postadressen ändrades. Konfigurera 2FA igen.'
  }
})
watch(twoFactorEnabled, enabled => {
  if (!enabled) {
    twoFactorSetup.value = null
    twoFactorQrCode.value = ''
    twoFactorCode.value = ''
    twoFactorSetupError.value = ''
  }
})
const setupTwoFactor = async () => {
  if (!isValidEmail(normalizedSignupEmail.value)) {
    twoFactorSetupError.value = 'Ange en giltig e-postadress med domän, till exempel namn@foretag.se.'
    return
  }
  twoFactorSetupLoading.value = true
  twoFactorSetupError.value = ''
  twoFactorSetup.value = null
  twoFactorQrCode.value = ''
  try {
    const response = await fetch('http://localhost:8000/account-applications/two-factor/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: normalizedSignupEmail.value }),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(apiErrorMessage(result, 'Kunde inte starta 2FA-konfigurationen.'))
    twoFactorSetup.value = { ...result, email: normalizedSignupEmail.value }
    try {
      twoFactorQrCode.value = await QRCode.toDataURL(result.otpauth_uri, {
        errorCorrectionLevel: 'M',
        margin: 2,
        width: 220,
      })
    } catch {
      twoFactorSetupError.value = 'QR-koden kunde inte skapas. Använd nyckeln manuellt i din authenticator-app.'
    }
    twoFactorCode.value = ''
  } catch (error) {
    twoFactorSetupError.value = error instanceof Error ? error.message : 'Kunde inte starta 2FA-konfigurationen.'
  } finally {
    twoFactorSetupLoading.value = false
  }
}
const submitSignup = async () => {
  showSignupErrors.value = true
  signupError.value = ''
  if (!canRegister.value) return
  try {
    const response = await fetch('http://localhost:8000/account-applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: signupForm.name.trim(),
        email: normalizedSignupEmail.value,
        password: signupForm.password,
        ...(twoFactorEnabled.value && twoFactorSetup.value
          ? { two_factor_secret: twoFactorSetup.value.secret, two_factor_code: twoFactorCode.value }
          : {}),
      }),
    })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(apiErrorMessage(result, 'Kunde inte skicka registreringen.'))
    showSignupForm.value = false
    showPendingMessage.value = true
  } catch (error) {
    signupError.value = error instanceof Error ? error.message : 'Kunde inte skicka registreringen.'
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
    <div v-if="showSignupForm" class="signup-backdrop" @click.self="showSignupForm = false">
      <div class="signup-card">
        <button class="signup-close" @click="showSignupForm = false">×</button>
        <div class="signup-icon">▤</div>
        <h2>Smart Lagring</h2>
        <small>WAREHOUSE MANAGEMENT SYSTEM</small>
        <p>Skapa konto</p>
        <form @submit.prevent="submitSignup">
          <label>Namn<input v-model="signupForm.name" placeholder="Förnamn Efternamn" required /></label>
          <label>E-postadress<input type="email" :class="{ invalid: showSignupErrors && !isValidEmail(signupForm.email.trim()) }" v-model="signupForm.email" placeholder="namn@foretag.se" required /></label>
          <label>Lösenord<input :class="{ invalid: showSignupErrors && signupForm.password.length < 8 }" v-model="signupForm.password" type="password" placeholder="••••••••" required /></label>
          <label>Bekräfta lösenord<input :class="{ invalid: showSignupErrors && (!signupForm.confirmPassword || signupForm.password !== signupForm.confirmPassword) }" v-model="signupForm.confirmPassword" type="password" placeholder="••••••••" required /></label>
          <label class="two-factor-choice"><input v-model="twoFactorEnabled" type="checkbox" /> Aktivera tvåfaktorsautentisering</label>
          <div v-if="twoFactorEnabled" class="two-factor-enrollment">
            <button type="button" class="two-factor-setup-button" :disabled="twoFactorSetupLoading" @click="setupTwoFactor">{{ twoFactorSetupLoading ? 'Förbereder...' : twoFactorSetup ? 'Skapa ny authenticator-nyckel' : 'Konfigurera authenticator' }}</button>
            <div v-if="twoFactorSetup" class="two-factor-secret">
              <p>Skanna QR-koden med din authenticator-app.</p>
              <img v-if="twoFactorQrCode" class="two-factor-qr" :src="twoFactorQrCode" alt="QR-kod för att konfigurera tvåfaktorsautentisering" />
              <details>
                <summary>Kan inte skanna? Visa nyckeln manuellt</summary>
                <code>{{ twoFactorSetup.secret }}</code>
              </details>
              <label>6-siffrig kod<input v-model="twoFactorCode" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" placeholder="000000" required /></label>
            </div>
            <p v-if="twoFactorSetupError" class="signup-errors" role="alert">{{ twoFactorSetupError }}</p>
          </div>
          <div v-if="showSignupErrors && !canRegister" class="signup-errors">Fyll i alla fält. Lösenordet måste ha minst 8 tecken och matcha bekräftelsen. Om 2FA är aktiverat, konfigurera authenticator och ange aktuell sexsiffrig kod.</div>
          <p v-if="signupError" class="signup-errors" role="alert">{{ signupError }}</p>
          <button type="submit">Registrera konto →</button>
        </form>
        <footer>Har du redan ett konto? <b @click="$emit('login'); showSignupForm = false">Logga in</b><small>© Smart Lagring. Alla rättigheter förbehålls.</small></footer>
      </div>
    </div>
    <div v-if="showLoginForm" class="login-backdrop" @click.self="showLoginForm = false"><div class="login-card"><button class="signup-close" @click="showLoginForm = false">×</button><div class="signup-icon">▤</div><h2>Smart Lagring</h2><small>WAREHOUSE MANAGEMENT SYSTEM</small><p>Inloggning</p><form @submit.prevent="submitLogin"><label>E-postadress<input v-model="loginForm.email" type="email" placeholder="namn@foretag.se" required /></label><label>Lösenord<input v-model="loginForm.password" type="password" placeholder="••••••••" required /></label><label v-if="loginRequiresTwoFactor">Authenticator-kod<input v-model="loginTwoFactorCode" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" placeholder="000000" required /></label><a>Glömt lösenord?</a><p v-if="loginError" class="login-error">{{ loginError }}</p><button type="submit">{{ loginRequiresTwoFactor ? 'Verifiera kod →' : 'Logga in →' }}</button><button v-if="loginRequiresTwoFactor" type="button" class="two-factor-back" @click="loginRequiresTwoFactor = false; loginTwoFactorCode = ''; loginError = ''">Tillbaka</button></form><footer>© 2026 Smart Lagring. Alla rättigheter förbehålls.</footer></div></div>
    <div v-if="showPendingMessage" class="pending-backdrop" @click.self="showPendingMessage = false"><div class="pending-card"><div class="pending-icon">✓</div><h2>Registrering mottagen</h2><p>Din registrering väntar på validering.</p><button @click="showPendingMessage = false">Stäng</button></div></div>
  </div>
</template>
