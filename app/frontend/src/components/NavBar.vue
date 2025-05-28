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
    <div class="container">
      <div class="navbar-content">
        <!-- Brand -->
        <div class="navbar-brand">
          <router-link to="/" class="brand-link">
            <div class="brand-icon">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="32" height="32" rx="8" fill="currentColor"/>
                <path d="M8 12h16M8 16h16M8 20h10" stroke="white" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="brand-text">
              <span class="brand-name">Arbeidsdeskundige</span>
              <span class="brand-subtitle">AI Rapport Generator</span>
            </div>
          </router-link>
        </div>
        
        <!-- Navigation Menu -->
        <div class="navbar-menu">
          <template v-if="isLoggedIn">
            <router-link to="/cases" class="nav-link">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4z"/>
              </svg>
              Mijn Cases
            </router-link>
            <router-link :to="{ name: 'profile' }" class="nav-link">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
              </svg>
              Mijn Profiel
            </router-link>
            <button @click="handleLogout" class="nav-link nav-button">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clip-rule="evenodd"/>
              </svg>
              Uitloggen
            </button>
          </template>
          <template v-else>
            <router-link to="/login" class="nav-link nav-login">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M3 3a1 1 0 011 1v12a1 1 0 11-2 0V4a1 1 0 011-1zm7.707 3.293a1 1 0 010 1.414L9.414 9H17a1 1 0 110 2H9.414l1.293 1.293a1 1 0 01-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
              Inloggen
            </router-link>
          </template>
        </div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-hover) 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(8px);
}

.navbar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) 0;
}

/* Brand Styling */
.navbar-brand {
  flex-shrink: 0;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--text-inverse);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.brand-link:hover {
  color: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}

.brand-icon {
  color: var(--text-inverse);
  transition: all var(--transition-fast);
}

.brand-link:hover .brand-icon {
  transform: rotate(5deg) scale(1.05);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
  letter-spacing: -0.025em;
}

.brand-subtitle {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  opacity: 0.8;
  line-height: var(--line-height-tight);
  letter-spacing: 0.025em;
  text-transform: uppercase;
}

/* Navigation Menu */
.navbar-menu {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--text-inverse);
  text-decoration: none;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius);
  transition: all var(--transition-fast);
  position: relative;
  white-space: nowrap;
}

.nav-link:hover {
  color: var(--text-inverse);
  background-color: rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.nav-link.router-link-active {
  background-color: rgba(255, 255, 255, 0.15);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
}

.nav-button {
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
}

.nav-login {
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.nav-login:hover {
  background-color: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
}

.nav-icon {
  width: 18px;
  height: 18px;
  opacity: 0.9;
  transition: all var(--transition-fast);
}

.nav-link:hover .nav-icon {
  opacity: 1;
  transform: scale(1.1);
}

/* Responsive Design */
@media (max-width: 768px) {
  .navbar-content {
    padding: var(--spacing-md) 0;
  }
  
  .brand-text {
    display: none;
  }
  
  .navbar-menu {
    gap: var(--spacing-xs);
  }
  
  .nav-link {
    padding: var(--spacing-sm);
    font-size: 0;
  }
  
  .nav-link .nav-icon {
    width: 20px;
    height: 20px;
  }
  
  /* Show tooltips on mobile */
  .nav-link::after {
    content: attr(data-tooltip);
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: var(--gray-900);
    color: var(--text-inverse);
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius);
    font-size: var(--font-size-xs);
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: all var(--transition-fast);
    z-index: 60;
  }
  
  .nav-link:hover::after {
    opacity: 1;
    transform: translateX(-50%) translateY(4px);
  }
}

@media (max-width: 480px) {
  .container {
    padding: 0 var(--spacing-md);
  }
  
  .navbar-content {
    padding: var(--spacing-sm) 0;
  }
  
  .brand-name {
    font-size: var(--font-size-lg);
  }
}
</style>
