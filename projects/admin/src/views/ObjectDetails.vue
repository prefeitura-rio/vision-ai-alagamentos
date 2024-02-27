<template>
  <div>
    <h2>Object Details</h2>
    <div class="mb-3">
      <label for="id" class="form-label">ID</label>
      <input type="text" id="id" v-model="object.id" class="form-control" disabled>
    </div>
    <div class="mb-3">
      <label for="name" class="form-label">Name</label>
      <input type="text" id="name" v-model="object.name" class="form-control" @input="enableSave">
    </div>
    <div class="mb-3">
      <label for="slug" class="form-label">Slug</label>
      <input type="text" id="slug" v-model="object.slug" class="form-control" @input="enableSave">
    </div>
    <div class="mb-3">
      <label for="title" class="form-label">Title</label>
      <input type="text" id="title" v-model="object.title" class="form-control" @input="enableSave">
    </div>
    <div class="mb-3">
      <label for="question" class="form-label">Question</label>
      <input type="text" id="question" v-model="object.question" class="form-control" @input="enableSave">
    </div>
    <div class="mb-3">
      <label for="explanation" class="form-label">Explanation</label>
      <textarea id="explanation" v-model="object.explanation" class="form-control" rows="4" @input="enableSave"></textarea>
    </div>
    <button v-if="isModified" @click="saveChanges" class="btn btn-primary">Save</button>
    <button @click="deleteObject" class="btn btn-danger">Delete</button>

    <div class="my-4"></div>

    <h3>Associated Labels</h3>
    <table class="table">
      <!-- Table for associated labels -->
      <thead>
        <tr>
          <th>ID</th>
          <th>Value</th>
          <th>Text</th>
          <th>Criteria</th>
          <th>Identification Guide</th>
        </tr>
      </thead>
      <tbody>
        <!-- Loop through associated labels -->
        <tr v-for="label in object.labels" :key="label.id">
          <td>{{ label.id }}</td>
          <td>{{ label.value }}</td>
          <td>{{ label.text }}</td>
          <td>{{ label.criteria }}</td>
          <td>{{ label.identification_guide }}</td>
        </tr>
      </tbody>
    </table>

    <div class="my-4">
      <h3>Associated Cameras</h3>
      <div class="mb-3">
        <label for="cameraId" class="form-label">Camera ID</label>
        <input type="text" id="cameraId" v-model="newCameraId" class="form-control">
      </div>
      <button @click="associateCamera" class="btn btn-primary">Associate Camera</button>
      <div class="my-4"></div>
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th></th> <!-- Empty header for delete button column -->
          </tr>
        </thead>
        <tbody>
          <tr v-for="camera in cameras" :key="camera.id">
            <td>{{ camera.id }}</td>
            <td>{{ camera.name }}</td>
            <td>
              <button class="btn btn-danger" @click="deleteCamera(camera.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination controls for associated cameras -->
      <div>
        <button :disabled="currentPage === 1" @click="prevPage" class="btn btn-secondary">Previous</button>
        <span>Page {{ currentPage }} of {{ totalPages }}</span>
        <button :disabled="currentPage === totalPages" @click="nextPage" class="btn btn-secondary">Next</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const router = useRouter()
const objectId = router.currentRoute.value.params.id
const object = ref({})
const originalObject = ref({})
const isModified = ref(false)
const cameras = ref([])
const pageSize = 10
const currentPage = ref(1)
const totalPages = ref(1)
const newCameraId = ref('') // Input field for camera ID

const getObjectDetails = async () => {
  try {
    const response = await apiRequest.get(`/objects/${objectId}`)
    object.value = { ...response }
    originalObject.value = { ...response }
    await getAssociatedCameras()
  } catch (error) {
    console.error('Error fetching object details:', error)
  }
}

const enableSave = () => {
  isModified.value = true
}

const saveChanges = async () => {
  try {
    await apiRequest.put(`/objects/${objectId}`, object.value)
    originalObject.value = { ...object.value }
    isModified.value = false
    alert('Changes saved successfully!')
  } catch (error) {
    console.error('Error saving changes:', error)
  }
}

const deleteObject = async () => {
  try {
    if (confirm('Are you sure you want to delete this object?')) {
      await apiRequest.delete(`/objects/${objectId}`)
      router.push('/objects')
    }
  } catch (error) {
    console.error('Error deleting object:', error)
  }
}

const getAssociatedCameras = async () => {
  try {
    const response = await apiRequest.get(`/objects/${objectId}/cameras?page=${currentPage.value}&size=${pageSize}`)
    cameras.value = response.items
    totalPages.value = response.pages
  } catch (error) {
    console.error('Error fetching associated cameras:', error)
  }
}

const deleteCamera = async (cameraId: string) => {
  try {
    if (confirm('Are you sure you want to remove this camera association?')) {
      await apiRequest.delete(`/objects/${objectId}/cameras/${cameraId}`)
      await getAssociatedCameras()
    }
  } catch (error) {
    console.error('Error deleting camera association:', error)
  }
}

const prevPage = async () => {
  if (currentPage.value > 1) {
    currentPage.value -= 1
    await getAssociatedCameras()
  }
}

const nextPage = async () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value += 1
    await getAssociatedCameras()
  }
}

const associateCamera = async () => {
  try {
    if (newCameraId.value.trim() === '') {
      alert('Please enter a camera ID.')
      return
    }

    await apiRequest.post(`/objects/${objectId}/cameras/${newCameraId.value}`)
    await getAssociatedCameras() // Refresh cameras list after association
    newCameraId.value = '' // Clear input field
    alert('Camera associated successfully!')
  } catch (error) {
    console.error('Error associating camera:', error)
  }
}

onMounted(() => {
  getObjectDetails()
})
</script>
