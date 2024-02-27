<template>
  <div>
    <h2>Camera Snapshots</h2>
    <div class="mb-3">
      <label for="minuteInterval" class="form-label">Minute Interval</label>
      <input
        type="number"
        id="minuteInterval"
        v-model.number="minuteInterval"
        class="form-control"
        @input="updateSnapshots"
      />
    </div>
    <div v-if="snapshots.length === 0" class="alert alert-info" role="alert">
      No snapshots found for the selected minute interval.
    </div>
    <div v-else>
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Image URL</th>
            <!-- <th>Identifications</th> -->
          </tr>
        </thead>
        <tbody>
          <tr v-for="snapshot in snapshots" :key="snapshot.id">
            <td>{{ snapshot.id }}</td>
            <td>{{ formatTimestamp(snapshot.timestamp) }}</td>
            <td>
              <a :href="snapshot.image_url" target="_blank">{{ snapshot.image_url }}</a>
            </td>
            <!-- <td>
              <router-link :to="`/cameras/${cameraId}/snapshots/${snapshot.id}/identifications`" class="btn btn-primary">Identifications</router-link>
            </td> -->
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const route = useRoute()
const cameraId = computed(() => route.params.id)
const snapshots = ref([])
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = 10
const minuteInterval = ref(60) // Default to 60 minutes

onMounted(async () => {
  await getSnapshots()
})

const updateSnapshots = async () => {
  currentPage.value = 1 // Reset page to 1 when updating snapshots
  await getSnapshots()
}

const getSnapshots = async () => {
  try {
    const response = await apiRequest.get(
      `/cameras/${cameraId.value}/snapshots?page=${currentPage.value}&size=${pageSize}&minute_interval=${minuteInterval.value}`
    )
    snapshots.value = response.items
    totalPages.value = response.pages
  } catch (error) {
    console.error('Error fetching snapshots:', error)
  }
}

const prevPage = async () => {
  if (currentPage.value > 1) {
    currentPage.value--
    await getSnapshots()
  }
}

const nextPage = async () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    await getSnapshots()
  }
}

const formatTimestamp = (timestamp: string) => {
  // Parse timestamp to a more friendly format
  const date = new Date(timestamp)
  return date.toLocaleString()
}
</script>
