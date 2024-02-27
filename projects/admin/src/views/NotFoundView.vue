<template>
  <div class="error-container d-flex justify-content-center align-items-center flex-column">
    <h1 class="error-title">404</h1>
    <p class="error-text">Oops! This is not the page you're looking for.</p>
    <router-link to="/" class="btn btn-primary error-link">Take me home!</router-link>
  </div>
</template>

<script>
export default {
  name: 'NotFound'
}
</script>

<style scoped>
.error-container {
  height: 100vh;
}

.error-title {
  font-size: 5rem;
  margin-bottom: 20px;
}

.error-text {
  font-size: 1.5rem;
  margin-bottom: 40px;
}

.error-link {
  font-size: 1rem;
}
</style>
