<template>
  <div>
    <h2>Camera Details</h2>
    <router-link :to="`/cameras/${camera.id}/snapshots`" class="btn btn-primary mb-3"
      >Snapshots</router-link
    >
    <div class="mb-3">
      <label for="id" class="form-label">ID</label>
      <input type="text" id="id" v-model="camera.id" class="form-control" disabled />
    </div>
    <div class="mb-3">
      <label for="name" class="form-label">Name</label>
      <input type="text" id="name" v-model="camera.name" class="form-control" @input="enableSave" />
    </div>
    <div class="mb-3">
      <label for="rtsp_url" class="form-label">RTSP URL</label>
      <input
        type="text"
        id="rtsp_url"
        v-model="camera.rtsp_url"
        class="form-control"
        @input="enableSave"
      />
    </div>
    <div class="mb-3">
      <label for="update_interval" class="form-label">Update Interval (seconds)</label>
      <input
        type="number"
        id="update_interval"
        v-model.number="camera.update_interval"
        class="form-control"
        @input="enableSave"
      />
    </div>
    <div class="mb-3">
      <label for="latitude" class="form-label">Latitude</label>
      <input
        type="number"
        id="latitude"
        v-model.number="camera.latitude"
        class="form-control"
        @input="enableSave"
      />
    </div>
    <div class="mb-3">
      <label for="longitude" class="form-label">Longitude</label>
      <input
        type="number"
        id="longitude"
        v-model.number="camera.longitude"
        class="form-control"
        @input="enableSave"
      />
    </div>
    <button v-if="isModified" @click="saveChanges" class="btn btn-primary">Save</button>
    <button @click="deleteCamera" class="btn btn-danger">Delete</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const router = useRouter()
const route = useRoute()
const cameraId = computed(() => route.params.id)
const camera = ref({})
const originalCamera = ref({})
const isModified = ref(false)

onMounted(async () => {
  await getCameraDetails()
})

const getCameraDetails = async () => {
  try {
    const response = await apiRequest.get(`/cameras/${cameraId.value}`)
    camera.value = { ...response }
    originalCamera.value = { ...response }
  } catch (error) {
    console.error('Error fetching camera details:', error)
  }
}

const enableSave = () => {
  isModified.value = true
}

const saveChanges = async () => {
  try {
    await apiRequest.put(`/cameras/${cameraId.value}`, camera.value)
    originalCamera.value = { ...camera.value }
    isModified.value = false
    alert('Changes saved successfully!')
  } catch (error) {
    console.error('Error saving changes:', error)
  }
}

const deleteCamera = async () => {
  try {
    if (confirm('Are you sure you want to delete this camera?')) {
      await apiRequest.delete(`/cameras/${cameraId.value}`)
      router.push('/cameras') // Redirect to cameras list after deletion
    }
  } catch (error) {
    console.error('Error deleting camera:', error)
  }
}
</script>
