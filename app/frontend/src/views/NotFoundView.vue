<template>
  <div class="not-found">
    <h1>404</h1>
    <h2>Pagina niet gevonden</h2>
    <p>De pagina die u zoekt bestaat niet of is verplaatst.</p>
    <router-link to="/" class="btn btn-primary">Terug naar home</router-link>
  </div>
</template>

<style scoped>
.not-found {
  text-align: center;
  padding: 3rem 1rem;
}

.not-found h1 {
  font-size: 6rem;
  margin-bottom: 0;
  color: var(--primary-color);
}

.not-found h2 {
  margin-bottom: 1.5rem;
  font-weight: 400;
}

.not-found p {
  margin-bottom: 2rem;
  color: var(--text-light);
}
</style>
