<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isLoggedIn = computed(() => authStore.isLoggedIn)

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <router-link to="/">AD-Rapport Generator</router-link>
    </div>
    
    <div class="navbar-menu">
      <template v-if="isLoggedIn">
        <router-link to="/cases">Mijn Cases</router-link>
        <router-link to="/profile">Mijn Profiel</router-link>
        <a href="#" @click.prevent="handleLogout">Uitloggen</a>
      </template>
      <template v-else>
        <router-link to="/login">Inloggen</router-link>
      </template>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: var(--primary-color);
  color: white;
}

.navbar-brand a {
  font-size: 1.5rem;
  font-weight: bold;
  color: white;
  text-decoration: none;
}

.navbar-menu {
  display: flex;
  gap: 1.5rem;
}

.navbar-menu a {
  color: white;
  text-decoration: none;
  padding: 0.5rem 0;
  position: relative;
}

.navbar-menu a:hover {
  text-decoration: none;
}

.navbar-menu a:after {
  content: '';
  position: absolute;
  width: 0;
  height: 2px;
  bottom: 0;
  left: 0;
  background-color: white;
  transition: width 0.3s;
}

.navbar-menu a:hover:after {
  width: 100%;
}
</style>
