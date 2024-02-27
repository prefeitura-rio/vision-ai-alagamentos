<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const cameras = ref([])
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = 20
const router = useRouter()

onMounted(async () => {
  await getPage(1)
})

const getPage = async (page: number) => {
  currentPage.value = page
  const response = await apiRequest.get(`/cameras?page=${currentPage.value}&size=${pageSize}`)
  cameras.value = response.items
  totalPages.value = response.pages
}

const prevPage = async () => {
  await getPage(currentPage.value - 1)
}

const nextPage = async () => {
  await getPage(currentPage.value + 1)
}

const deleteCamera = async (cameraId: string) => {
  if (confirm('Are you sure you want to remove this camera?')) {
    await apiRequest.delete(`/cameras/${cameraId}`)
    await getPage(currentPage.value)
  }
}

const createNewCamera = () => {
  router.push('/cameras/new')
}

const goToCameraDetail = (cameraId: string) => {
  router.push(`/cameras/${cameraId}`)
}
</script>

<template>
  <div>
    <h2>Cameras</h2>
    <button @click="createNewCamera" class="btn btn-success mb-3">Create New Camera</button>
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th></th>
          <!-- Empty header for snapshots button column -->
          <th></th>
          <!-- Empty header for delete button column -->
        </tr>
      </thead>
      <tbody>
        <tr v-for="camera in cameras" :key="camera.id">
          <td>
            <router-link
              :to="`/cameras/${camera.id}`"
              @click.native="goToCameraDetail(camera.id)"
              >{{ camera.id }}</router-link
            >
          </td>
          <td>{{ camera.name }}</td>
          <td>
            <router-link :to="`/cameras/${camera.id}/snapshots`" class="btn btn-primary"
              >Snapshots</router-link
            >
          </td>
          <td>
            <button class="btn btn-danger" @click="deleteCamera(camera.id)">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
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
