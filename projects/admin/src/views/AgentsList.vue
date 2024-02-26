<script setup>
import { ref, onMounted } from 'vue'
import { apiRequest } from '../_helpers/api-request'
import { RouterLink } from 'vue-router'

const agents = ref([])

onMounted(async () => {
    const response = await apiRequest.get("/agents")
    agents.value = response
})

</script>

<template>
  <div>
    <ul>
      <li v-for="agent in agents.items" :key="agent.id">
        <RouterLink :to="`/agents/${agent.id}`">{{ agent.name }} ({{ agent.id }})</RouterLink>
      </li>
    </ul>
  </div>
</template>