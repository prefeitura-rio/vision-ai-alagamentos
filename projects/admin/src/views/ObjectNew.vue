<template>
  <div>
    <h2>Create New Object</h2>
    <div class="mb-3">
      <label for="name" class="form-label">Name</label>
      <input type="text" id="name" v-model="object.name" class="form-control">
    </div>
    <div class="mb-3">
      <label for="slug" class="form-label">Slug</label>
      <input type="text" id="slug" v-model="object.slug" class="form-control">
    </div>
    <div class="mb-3">
      <label for="title" class="form-label">Title</label>
      <input type="text" id="title" v-model="object.title" class="form-control">
    </div>
    <div class="mb-3">
      <label for="question" class="form-label">Question</label>
      <input type="text" id="question" v-model="object.question" class="form-control">
    </div>
    <div class="mb-3">
      <label for="explanation" class="form-label">Explanation</label>
      <textarea id="explanation" v-model="object.explanation" class="form-control" rows="4"></textarea>
    </div>
    <button @click="createObject" class="btn btn-primary">Create</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const router = useRouter()
const object = ref({
  name: '',
  slug: '',
  title: '',
  question: '',
  explanation: ''
})

const createObject = async () => {
  try {
    const response = await apiRequest.post('/objects', object.value)
    alert('Object created successfully!')
    router.push(`/objects/${response.id}`)
  } catch (error) {
    console.error('Error creating object:', error)
  }
}
</script>
