<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const errorMessage = ref('')
const isRegistering = ref(false)

const login = async () => {
  if (!email.value || !password.value) {
    errorMessage.value = 'Vul alstublieft zowel email als wachtwoord in'
    return
  }
  
  try {
    errorMessage.value = ''
    await authStore.login(email.value, password.value)
    
    // Redirect to intended page or cases page
    const redirectPath = route.query.redirect?.toString() || '/'
    
    // Use window.location for harder refresh instead of router.push
    window.location.href = redirectPath
  } catch (error) {
    console.error('Login error:', error)
    errorMessage.value = 'Inloggen mislukt. Controleer uw gegevens.'
  }
}

const register = async () => {
  if (!email.value || !password.value) {
    errorMessage.value = 'Vul alstublieft zowel email als wachtwoord in'
    return
  }
  
  if (password.value.length < 6) {
    errorMessage.value = 'Wachtwoord moet minimaal 6 tekens bevatten'
    return
  }
  
  try {
    errorMessage.value = ''
    await authStore.register(email.value, password.value)
    isRegistering.value = false
    errorMessage.value = 'Registratie succesvol! U kunt nu inloggen.'
  } catch (error) {
    console.error('Registration error:', error)
    errorMessage.value = 'Registratie mislukt. Probeer een ander e-mailadres.'
  }
}

const toggleForm = () => {
  isRegistering.value = !isRegistering.value
  errorMessage.value = ''
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h2 v-if="isRegistering">Registreren</h2>
      <h2 v-else>Inloggen</h2>
      
      <div v-if="errorMessage" class="alert alert-danger">
        {{ errorMessage }}
      </div>
      
      <div class="form-group">
        <label for="email">E-mail</label>
        <input 
          type="email" 
          id="email" 
          v-model="email" 
          placeholder="uw@email.nl"
          autocomplete="email"
        >
      </div>
      
      <div class="form-group">
        <label for="password">Wachtwoord</label>
        <input 
          type="password" 
          id="password" 
          v-model="password"
          autocomplete="current-password"
        >
      </div>
      
      <div class="form-actions">
        <button v-if="isRegistering" @click="register" class="btn btn-primary">Registreren</button>
        <button v-else @click="login" class="btn btn-primary">Inloggen</button>
      </div>
      
      <div class="form-toggle">
        <a href="#" @click.prevent="toggleForm">
          <span v-if="isRegistering">Heeft u al een account? Log in</span>
          <span v-else>Nog geen account? Registreer</span>
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 70vh;
}

.login-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 2rem;
  width: 100%;
  max-width: 400px;
}

.login-card h2 {
  text-align: center;
  color: var(--primary-color);
  margin-bottom: 1.5rem;
}

.form-actions {
  margin-top: 1.5rem;
}

.form-actions button {
  width: 100%;
}

.form-toggle {
  margin-top: 1rem;
  text-align: center;
  font-size: 0.9rem;
}
</style>
