<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router';

import { apiRequest } from '../_helpers/api-request'
import { RouterLink } from 'vue-router'

const agentData = ref({
  id: '',
  name: '',
  slug: '',
  auth_sub: '',
  last_heartbeat: ''
})
const displayedCameras = ref([])
const currentPage = ref(1)
const totalPages = ref(1)
const route = useRoute()
const agentId = computed(() => route.params.id)
const addCameraId = ref('')

apiRequest.get(`/agents/${agentId.value}`).then(response =>
  agentData.value = response
)


const getPage = (page: number) => {
  currentPage.value = page
  apiRequest.get(`/agents/${agentId.value}/cameras?page=${currentPage.value}`).then(response => {
    displayedCameras.value = response.items
    totalPages.value = response.pages
  }
  )
}

const prevPage = () => {
  getPage(currentPage.value - 1)
}

const nextPage = () => {
  getPage(currentPage.value + 1)
}

const deleteCamera = (cameraId: string) => {
  if (confirm('Are you sure you want to remove this camera?')) {
    apiRequest.delete(`/agents/${agentId.value}/cameras/${cameraId}`).then(() => {
      getPage(currentPage.value)
    })
    getPage(currentPage.value)
  }
}

const addCamera = () => {
  apiRequest.post(`/agents/${agentId.value}/cameras/${addCameraId.value}`).then(() => {
    getPage(currentPage.value)
  })
}

onMounted(() => {
  getPage(1)
})
</script>

<template>
  <div>
    <h1>Agent Details</h1>
    <div>
      <p><strong>ID:</strong> {{ agentData.id }}</p>
      <p><strong>Name:</strong> {{ agentData.name }}</p>
      <p><strong>Slug:</strong> {{ agentData.slug }}</p>
      <p><strong>Auth Sub:</strong> {{ agentData.auth_sub }}</p>
      <p><strong>Last Heartbeat:</strong> {{ agentData.last_heartbeat }}</p>
    </div>
    <h2>Cameras</h2>
    <div class="mb-3">
      <div class="input-group">
        <input type="text" class="form-control" v-model="addCameraId" placeholder="Enter camera ID">
        <button class="btn btn-primary" @click="addCamera">Add Camera</button>
      </div>
    </div>
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="camera in displayedCameras" :key="camera.id">
          <td>{{ camera.id }}</td>
          <td>{{ camera.name }}</td>
          <td>
            <button class="btn btn-danger" @click="deleteCamera(camera.id)">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div>
      <button :disabled="currentPage === 1" @click="prevPage" class="btn btn-secondary">Previous</button>
      <span>Page {{ currentPage }} of {{ totalPages }}</span>
      <button :disabled="currentPage === totalPages" @click="nextPage" class="btn btn-secondary">Next</button>
    </div>
  </div>
</template>
