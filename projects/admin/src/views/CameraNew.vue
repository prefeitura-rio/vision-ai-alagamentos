<template>
  <div>
    <h2>Create New Camera</h2>
    <form @submit.prevent="submitForm">
      <div class="mb-3">
        <label for="id" class="form-label">ID <span class="text-danger">*</span></label>
        <input type="text" id="id" v-model.trim="formData.id" class="form-control" required />
      </div>
      <div class="mb-3">
        <label for="name" class="form-label">Name</label>
        <input type="text" id="name" v-model.trim="formData.name" class="form-control" />
      </div>
      <div class="mb-3">
        <label for="rtsp_url" class="form-label">RTSP URL <span class="text-danger">*</span></label>
        <input
          type="text"
          id="rtsp_url"
          v-model.trim="formData.rtsp_url"
          class="form-control"
          required
        />
      </div>
      <div class="mb-3">
        <label for="update_interval" class="form-label"
          >Update Interval (seconds) <span class="text-danger">*</span></label
        >
        <input
          type="number"
          id="update_interval"
          v-model.number="formData.update_interval"
          class="form-control"
          required
        />
      </div>
      <div class="mb-3">
        <label for="latitude" class="form-label">Latitude <span class="text-danger">*</span></label>
        <input
          type="number"
          id="latitude"
          v-model.number="formData.latitude"
          class="form-control"
          required
        />
      </div>
      <div class="mb-3">
        <label for="longitude" class="form-label"
          >Longitude <span class="text-danger">*</span></label
        >
        <input
          type="number"
          id="longitude"
          v-model.number="formData.longitude"
          class="form-control"
          required
        />
      </div>
      <button type="submit" class="btn btn-primary">Create Camera</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { apiRequest } from '../_helpers/api-request'

const formData = ref({
  id: '',
  name: '',
  rtsp_url: '',
  update_interval: null,
  latitude: null,
  longitude: null
})

const submitForm = async () => {
  // If name is not filled, don't send empty string
  if (!formData.name) {
    delete formData.name
  }

  try {
    await apiRequest.post('/cameras', formData.value)
    // Optionally, you can add a success message or navigate to another page after successful creation
    alert('Camera created successfully!')
  } catch (error) {
    alert('Error creating camera: ' + error.message)
    // Optionally, you can display an error message to the user
  }
}
</script>
