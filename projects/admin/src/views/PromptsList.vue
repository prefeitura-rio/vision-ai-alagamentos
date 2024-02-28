<template>
  <div>
    <h2>Prompts</h2>
    <router-link to="/prompts/new" class="btn btn-success mb-3">Create New Prompt</router-link>
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Model</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="prompt in prompts" :key="prompt.id">
          <td>
            <router-link :to="`/prompts/${prompt.id}`">{{ prompt.id }}</router-link>
          </td>
          <td>{{ prompt.name }}</td>
          <td>{{ prompt.model }}</td>
          <td>
            <button class="btn btn-danger" @click="deletePrompt(prompt.id)">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
    <!-- Pagination controls -->
    <div>
      <button :disabled="currentPage === 1" @click="prevPage" class="btn btn-secondary">
        Previous
      </button>
      <span>Page {{ currentPage }} of {{ totalPages }}</span>
      <button :disabled="currentPage === totalPages" @click="nextPage" class="btn btn-secondary">
        Next
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const prompts = ref([])
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = 10

const getPage = async (page: number) => {
  currentPage.value = page
  try {
    const response = await apiRequest.get(`/prompts?page=${currentPage.value}&size=${pageSize}`)
    prompts.value = response.items
    totalPages.value = response.pages
  } catch (error) {
    console.error('Error fetching prompts:', error)
  }
}

const prevPage = async () => {
  if (currentPage.value > 1) {
    currentPage.value -= 1
    await getPage(currentPage.value)
  }
}

const nextPage = async () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value += 1
    await getPage(currentPage.value)
  }
}

const deletePrompt = async (promptId: string) => {
  try {
    if (confirm('Are you sure you want to delete this prompt?')) {
      await apiRequest.delete(`/prompts/${promptId}`)
      await getPage(currentPage.value)
    }
  } catch (error) {
    console.error('Error deleting prompt:', error)
  }
}

onMounted(() => {
  getPage(currentPage.value)
})
</script>
