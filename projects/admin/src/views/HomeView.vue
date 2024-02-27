<script setup lang="ts">
import { storeToRefs } from 'pinia'

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const { user: authUser } = storeToRefs(authStore)
</script>

<template>
  <div>
    <h4>Hello there!</h4>
    <router-link v-if="!authUser" to="/login" class="btn btn-primary error-link"
      >Log me in!</router-link
    >
  </div>
</template>
