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
  <nav class="navbar" role="navigation" aria-label="Hoofdnavigatie">
    <div class="container">
      <div class="navbar-content">
        <!-- Brand -->
        <div class="navbar-brand">
          <router-link 
            to="/" 
            class="brand-link"
            aria-label="Arbeidsdeskundige AI - Ga naar startpagina"
          >
            <div class="brand-icon" aria-hidden="true">
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
        <nav class="navbar-menu" role="menubar" aria-label="Gebruikersmenu">
          <template v-if="isLoggedIn">
            <router-link 
              to="/cases" 
              class="nav-link"
              role="menuitem"
              aria-label="Ga naar mijn cases overzicht"
            >
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4z"/>
              </svg>
              <span class="nav-text">Mijn Cases</span>
            </router-link>
            <router-link 
              :to="{ name: 'profile' }" 
              class="nav-link"
              role="menuitem"
              aria-label="Ga naar mijn profiel instellingen"
            >
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
              </svg>
              <span class="nav-text">Mijn Profiel</span>
            </router-link>
            <button 
              @click="handleLogout" 
              class="nav-link nav-button"
              role="menuitem"
              aria-label="Uitloggen uit de applicatie"
            >
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clip-rule="evenodd"/>
              </svg>
              <span class="nav-text">Uitloggen</span>
            </button>
          </template>
          <template v-else>
            <router-link 
              to="/login" 
              class="nav-link nav-login"
              role="menuitem"
              aria-label="Inloggen in de applicatie"
            >
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M3 3a1 1 0 011 1v12a1 1 0 11-2 0V4a1 1 0 011-1zm7.707 3.293a1 1 0 010 1.414L9.414 9H17a1 1 0 110 2H9.414l1.293 1.293a1 1 0 01-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
              <span class="nav-text">Inloggen</span>
            </router-link>
          </template>
        </nav>
      </div>
    </div>
  </nav>
</template>

<style scoped>
/* Ultra-Modern Navigation with Glass Effect */
.navbar {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 8px 32px -8px rgba(37, 99, 235, 0.08), 0 2px 12px -2px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.navbar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) 0;
  position: relative;
}

.navbar-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, 
    rgba(37, 99, 235, 0.02) 0%, 
    rgba(147, 197, 253, 0.03) 50%, 
    rgba(37, 99, 235, 0.01) 100%
  );
  pointer-events: none;
}

/* Elevated Brand Styling */
.navbar-brand {
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  color: var(--text-primary);
  text-decoration: none;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: var(--radius-xl);
  padding: var(--spacing-md) var(--spacing-lg);
  background: linear-gradient(135deg, 
    rgba(37, 99, 235, 0.08) 0%, 
    rgba(147, 197, 253, 0.05) 100%
  );
  border: 1px solid rgba(37, 99, 235, 0.12);
  position: relative;
  overflow: hidden;
}

.brand-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(37, 99, 235, 0.08), 
    transparent
  );
  transition: left 0.6s ease;
}

.brand-link:hover::before {
  left: 100%;
}

.brand-link:hover {
  background: linear-gradient(135deg, 
    rgba(37, 99, 235, 0.15) 0%, 
    rgba(147, 197, 253, 0.10) 100%
  );
  border-color: rgba(37, 99, 235, 0.25);
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 12px 30px -8px rgba(37, 99, 235, 0.25);
}

.brand-icon {
  font-size: 2.8rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 4px 8px rgba(37, 99, 235, 0.3));
  position: relative;
  z-index: 1;
}

.brand-link:hover .brand-icon {
  transform: rotate(15deg) scale(1.2);
  filter: drop-shadow(0 6px 12px rgba(37, 99, 235, 0.4));
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

/* Premium Navigation Menu */
.navbar-menu {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  list-style: none;
  margin: 0;
  padding: var(--spacing-sm);
  background: rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-xl);
  border: 1px solid rgba(37, 99, 235, 0.08);
  backdrop-filter: blur(12px);
  position: relative;
  z-index: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: var(--font-size-sm);
  font-weight: 600;
  border-radius: var(--radius-lg);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  white-space: nowrap;
  overflow: hidden;
}

.nav-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, 
    rgba(37, 99, 235, 0.1) 0%, 
    rgba(147, 197, 253, 0.08) 100%
  );
  opacity: 0;
  transition: opacity 0.3s ease;
}

.nav-link:hover::before {
  opacity: 1;
}

.nav-link:hover {
  color: var(--primary-color);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px -2px rgba(37, 99, 235, 0.2);
}

.nav-link.router-link-active {
  color: var(--primary-color);
  background: linear-gradient(135deg, 
    rgba(37, 99, 235, 0.12) 0%, 
    rgba(147, 197, 253, 0.08) 100%
  );
  font-weight: 700;
  box-shadow: 0 2px 8px -1px rgba(37, 99, 235, 0.25);
}

/* Enhanced Focus States for Accessibility */
.nav-link:focus-visible {
  outline: 3px solid rgba(255, 255, 255, 0.6);
  outline-offset: 2px;
  background-color: rgba(255, 255, 255, 0.2);
}

.brand-link:focus-visible {
  outline: 3px solid rgba(255, 255, 255, 0.6);
  outline-offset: 2px;
  border-radius: var(--radius);
}

/* Enhanced Responsive Design */
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
  
  .nav-text {
    display: none;
  }
  
  .nav-link {
    padding: var(--spacing-md);
    border-radius: 50%;
    width: 44px;
    height: 44px;
    justify-content: center;
  }
  
  .nav-icon {
    width: 24px;
    height: 24px;
  }
}

@media (max-width: 480px) {
  .container {
    padding: 0 var(--spacing-md);
  }
  
  .navbar-menu {
    gap: var(--spacing-xs);
  }
  
  .nav-link {
    padding: var(--spacing-sm);
    width: 40px;
    height: 40px;
  }
  
  .nav-icon {
    width: 20px;
    height: 20px;
  }
}

/* Loading States */
.nav-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Better hover animations */
.nav-link {
  position: relative;
  overflow: hidden;
}

.nav-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.nav-link:hover::before {
  left: 100%;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .navbar {
    border-bottom-width: 3px;
  }
  
  .nav-link {
    border: 2px solid transparent;
  }
  
  .nav-link:hover,
  .nav-link.router-link-active {
    border-color: rgba(255, 255, 255, 0.8);
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .nav-link,
  .brand-link {
    transition: none;
  }
  
  .nav-link::before {
    display: none;
  }
  
  .brand-link:hover {
    transform: none;
  }
  
  .nav-link:hover {
    transform: none;
  }
  
  .brand-link:hover .brand-icon {
    transform: none;
  }
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
    /* Touch-friendly sizing */
    min-width: 44px;
    min-height: 44px;
    padding: var(--spacing-sm);
    border-radius: var(--radius-md);
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
  }
  
  .nav-text {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
    line-height: 1;
    opacity: 0.9;
    text-align: center;
    white-space: nowrap;
  }
  
  .nav-link .nav-icon {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  }
  
  /* Enhanced touch feedback */
  .nav-link:active {
    transform: scale(0.95);
    background-color: rgba(255, 255, 255, 0.2);
  }
  
  /* Better hover states for touch devices */
  @media (hover: hover) {
    .nav-link:hover .nav-text {
      opacity: 1;
    }
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
