<template>
  <div>
    <h2>Objects List</h2>
    <router-link to="/objects/new" class="btn btn-primary mb-3">Create New Object</router-link>
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="object in objects" :key="object.id">
          <td>
            <router-link :to="`/objects/${object.id}`">{{ object.id }}</router-link>
          </td>
          <td>{{ object.name }}</td>
          <td>
            <button @click="deleteObject(object.id)" class="btn btn-danger">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const router = useRouter()
const objects = ref([])

const getObjects = async () => {
  try {
    const response = await apiRequest.get('/objects')
    objects.value = response.items
  } catch (error) {
    console.error('Error fetching objects:', error)
  }
}

const deleteObject = async (objectId: string) => {
  try {
    if (confirm('Are you sure you want to delete this object?')) {
      await apiRequest.delete(`/objects/${objectId}`)
      await getObjects()
    }
  } catch (error) {
    console.error('Error deleting object:', error)
  }
}

onMounted(() => {
  getObjects()
})
</script>
