<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'
const authStore = useAuthStore()
</script>

<template>
  <div class="app-container bg-light">
    <nav v-show="authStore.user" class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="#">Vision AI</a>
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarSupportedContent"
          aria-controls="navbarSupportedContent"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
          <ul class="navbar-nav me-auto mb-2 mb-lg-0">
            <li class="nav-item">
              <RouterLink to="/" class="nav-item nav-link">Home</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink to="/agents" class="nav-item nav-link">Agents</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink to="/cameras" class="nav-item nav-link">Cameras</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink to="/identifications" class="nav-item nav-link"
                >Identifications</RouterLink
              >
            </li>
            <li class="nav-item">
              <RouterLink to="/objects" class="nav-item nav-link">Objects</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink to="/prompts" class="nav-item nav-link">Prompts</RouterLink>
            </li>
          </ul>
          <form class="d-flex">
            <button class="btn btn-outline-success" @click="authStore.logout()" type="submit">
              Logout
            </button>
          </form>
        </div>
      </div>
    </nav>
    <div class="container pt-4 pb-4">
      <RouterView />
    </div>
  </div>
</template>

<style></style>
