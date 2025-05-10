<script setup lang="ts">
import { RouterView } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
</script>

<template>
  <header>
    <NavBar />
  </header>

  <main>
    <RouterView />
  </main>

  <footer>
    <div class="footer">
      <p>&copy; {{ new Date().getFullYear() }} AD-Rapport Generator</p>
    </div>
  </footer>
</template>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: Arial, sans-serif;
  background-color: #f5f5f5;
  color: #333;
}

main {
  min-height: calc(100vh - 140px);
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.footer {
  text-align: center;
  padding: 10px;
  background-color: #f0f0f0;
  font-size: 0.9rem;
  color: #666;
  border-top: 1px solid #ddd;
}
</style>
