<script setup lang="ts">
import { RouterView } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import NotificationContainer from '@/components/NotificationContainer.vue'
</script>

<template>
  <div id="app" class="app-layout">
    <!-- Header -->
    <header class="app-header">
      <NavBar />
    </header>

    <!-- Main Content -->
    <main class="app-main">
      <div class="container">
        <RouterView />
      </div>
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <div class="container">
        <div class="footer-content">
          <div class="footer-brand">
            <span class="footer-logo">📊</span>
            <div class="footer-text">
              <span class="footer-name">Arbeidsdeskundige AI</span>
              <span class="footer-tagline">Professionele rapporten, intelligent gemaakt</span>
            </div>
          </div>
          
          <div class="footer-links">
            <a href="#" class="footer-link">Privacy</a>
            <a href="#" class="footer-link">Voorwaarden</a>
            <a href="#" class="footer-link">Support</a>
          </div>
          
          <div class="footer-copy">
            <p>&copy; {{ new Date().getFullYear() }} Arbeidsdeskundige AI. Alle rechten voorbehouden.</p>
          </div>
        </div>
      </div>
    </footer>

    <!-- Notification System -->
    <NotificationContainer />
  </div>
</template>

<style>
/* App Layout */
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  flex-shrink: 0;
}

.app-main {
  flex: 1;
  padding: var(--spacing-2xl) 0;
  background-color: var(--bg-secondary);
}

/* Footer Styling */
.app-footer {
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--gray-800) 0%, var(--gray-900) 100%);
  color: var(--text-inverse);
  border-top: 1px solid var(--gray-700);
}

.footer-content {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-xl) 0;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.footer-logo {
  font-size: var(--font-size-2xl);
}

.footer-text {
  display: flex;
  flex-direction: column;
}

.footer-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
}

.footer-tagline {
  font-size: var(--font-size-xs);
  opacity: 0.8;
  line-height: var(--line-height-tight);
}

.footer-links {
  display: flex;
  gap: var(--spacing-lg);
}

.footer-link {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-size: var(--font-size-sm);
  transition: color var(--transition-fast);
}

.footer-link:hover {
  color: var(--text-inverse);
}

.footer-copy {
  text-align: right;
  margin: 0;
}

.footer-copy p {
  margin: 0;
  font-size: var(--font-size-xs);
  opacity: 0.7;
}

/* Responsive Footer */
@media (max-width: 768px) {
  .footer-content {
    grid-template-columns: 1fr;
    text-align: center;
    gap: var(--spacing-md);
  }
  
  .footer-copy {
    text-align: center;
  }
  
  .footer-links {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .app-main {
    padding: var(--spacing-lg) 0;
  }
  
  .footer-content {
    padding: var(--spacing-lg) 0;
  }
  
  .footer-brand {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
  
  .footer-text {
    text-align: center;
  }
  
  .footer-links {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
}

/* Global scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-muted);
}

::-webkit-scrollbar-thumb {
  background: var(--gray-400);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--gray-500);
}

/* Smooth scrolling */
html {
  scroll-behavior: smooth;
}

/* Focus improvements */
:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* Print styles */
@media print {
  .app-header,
  .app-footer {
    display: none;
  }
  
  .app-main {
    padding: 0;
  }
  
  .container {
    max-width: none;
    padding: 0;
  }
}
</style>
